from flask import Flask, render_template, request, redirect, url_for, session
from services.azure_devops_service import AzureDevOpsService
from services.ai_review_service import AIReviewService
import os
from dotenv import load_dotenv
import traceback
from datetime import datetime
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.context_processor
def utility_processor():
    def now(format):
        return datetime.now().strftime(format)
    return dict(now=now)

@app.context_processor
def inject_year():
    return {'year': datetime.now().year}

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/pull_requests', methods=['POST'])
def list_pull_requests():
    pat = request.form.get('pat')
    org_url = request.form.get('org_url')
    project = request.form.get('project')
    repository_name = request.form.get('repository')
    openai_key = request.form.get('openai_key')

    if not all([pat, org_url, project]):
        return "Missing required fields (PAT, Organization URL, Project)", 400

    try:
        # Store credentials in the session
        session['pat'] = pat
        session['org_url'] = org_url
        session['project'] = project
        session['repository_name'] = repository_name
        session['openai_key'] = openai_key

        devops_service = AzureDevOpsService(pat, org_url, project)
        pull_requests = devops_service.get_assigned_pull_requests()

        if repository_name:
            pull_requests = [pr for pr in pull_requests if pr.get('repository', {}).get('name') == repository_name]

        return render_template('pull_requests.html', pull_requests=pull_requests)
    except Exception as e:
        traceback.print_exc()
        return f"Error fetching pull requests: {type(e).__name__} - {str(e)}", 500

@app.route('/pull_requests', methods=['GET'])
def list_pull_requests_get():
    pat = session.get('pat')
    org_url = session.get('org_url')
    project = session.get('project')
    repository_name = session.get('repository_name')

    if not all([pat, org_url, project]):
        return redirect(url_for('index'))
        return
    try:
        devops_service = AzureDevOpsService(pat, org_url, project)
        pull_requests = devops_service.get_assigned_pull_requests()

        return render_template('pull_requests.html', pull_requests=pull_requests)

    except Exception as e:
        traceback.print_exc()
        return f"Error fetching pull requests: {type(e).__name__} - {str(e)}", 500

def process_diff(diff_text):
    """Process the diff text into a structured format"""
    if not diff_text or not isinstance(diff_text, str):
        return [{"file_path": "No changes", "language": "text", "lines": []}]

    files = []
    current_file = None
    current_lines = []
    old_line_num = 0
    new_line_num = 0
    
    for line in diff_text.splitlines():
        # New file
        if line.startswith('--- '):
            if current_file and current_lines:
                current_file['lines'] = current_lines
                files.append(current_file)
            current_file = None
            current_lines = []
            continue
            
        # File header
        if line.startswith('+++ '):
            file_path = line[6:].strip()  # Remove '+++ b/' prefix
            if file_path.startswith('b/'):
                file_path = file_path[2:]
            current_file = {
                'file_path': file_path,
                'language': file_path.split('.')[-1] if '.' in file_path else 'text',
                'lines': []
            }
            continue
            
        # Hunk header
        if line.startswith('@@'):
            try:
                hunk_info = line.split('@@')[1].strip()
                old_start = int(hunk_info.split(' ')[0].split(',')[0][1:])
                new_start = int(hunk_info.split(' ')[1].split(',')[0][1:])
                old_line_num = old_start
                new_line_num = new_start
                if current_file:
                    current_lines.append({
                        'type': 'diff-info',
                        'old_number': '...',
                        'new_number': '...',
                        'marker': '',
                        'content': line
                    })
            except Exception as e:
                print(f"Error parsing hunk header: {e}")
            continue

        if current_file is None:
            continue

        # Process the actual diff lines
        if line.startswith('+'):
            current_lines.append({
                'type': 'diff-addition',
                'old_number': '',
                'new_number': str(new_line_num),
                'marker': '+',
                'content': line[1:]
            })
            new_line_num += 1
        elif line.startswith('-'):
            current_lines.append({
                'type': 'diff-deletion',
                'old_number': str(old_line_num),
                'new_number': '',
                'marker': '-',
                'content': line[1:]
            })
            old_line_num += 1
        elif line.strip():
            current_lines.append({
                'type': 'diff-context',
                'old_number': str(old_line_num),
                'new_number': str(new_line_num),
                'marker': ' ',
                'content': line
            })
            old_line_num += 1
            new_line_num += 1

    if current_file and current_lines:
        current_file['lines'] = current_lines
        files.append(current_file)

    print(f"Processed {len(files)} files with {sum(len(f['lines']) for f in files)} lines")
    return files if files else [{"file_path": "No changes found", "language": "text", "lines": []}]

@app.route('/review/<repository_id>/<int:pr_id>', methods=['GET', 'POST'])
def review_pull_request(repository_id, pr_id):
    pat = session.get('pat')
    org_url = session.get('org_url')
    project = session.get('project')
    openai_key = session.get('openai_key')

    if not all([pat, org_url, project]):
        return redirect(url_for('index'))
        return

    devops_service = AzureDevOpsService(pat, org_url, project)
    ai_service = AIReviewService(openai_key)

    try:
        pr_details = devops_service.get_pull_request_details(repository_id, pr_id)
        code_diff = devops_service.get_pull_request_diff(repository_id, pr_id)
        
        print("Raw diff (first 500 chars):", code_diff[:500] if code_diff else None)
        
        if not code_diff:
            diff_message = [{"file_path": "No changes found", "language": "text", "lines": []}]
        else:
            diff_message = process_diff(code_diff)
            
        print(f"Processed {len(diff_message)} files")
        if diff_message and diff_message[0]['lines']:
            print(f"First file has {len(diff_message[0]['lines'])} lines")
        
        if request.method == 'GET':
            return render_template('review.html', pr=pr_details, diff_message=diff_message)

        elif request.method == 'POST':
            if 'get_ai_review' in request.form:
                if code_diff:
                    language = request.form.get('review_language', 'en')
                    review = ai_service.get_code_review(code_diff, language)
                else:
                    review = "Could not retrieve code diff."
                return render_template('review.html', pr=pr_details, diff_message=diff_message, review=review)

            else: #If not get_ai_review pressed
                return "Invalid request", 400

    except Exception as e:
        traceback.print_exc()
        return f"Error during review: {type(e).__name__} - {str(e)}", 500



@app.route('/manual_comment/<repository_id>/<int:pr_id>', methods=['POST'])
def manual_comment(repository_id, pr_id):
    pat = session.get('pat')
    org_url = session.get('org_url')
    project = session.get('project')
    if not all([pat, org_url, project]):
        return redirect(url_for('index'))
        return

    devops_service = AzureDevOpsService(pat, org_url, project)
    comment = request.form.get('manual_comment') # Get from form

    if not comment:
        return "No comment provided.", 400

    try:
        devops_service.create_pull_request_comment(repository_id, pr_id, comment)
        return redirect(url_for('review_pull_request', repository_id=repository_id, pr_id=pr_id))
    except Exception as e:
        traceback.print_exc()
        return f"Error sending manual comment: {type(e).__name__} - {str(e)}", 500


@app.route('/send_review/<repository_id>/<int:pr_id>', methods=['POST'])
def send_review(repository_id, pr_id):
    pat = session.get('pat')
    org_url = session.get('org_url')
    project = session.get('project')
    if not all([pat, org_url, project]):
        return redirect(url_for('index'))
        return

    devops_service = AzureDevOpsService(pat, org_url, project)
    review = request.form.get('review')

    if not review:
        return "No review to send.", 400

    try:
        devops_service.create_pull_request_comment(repository_id, pr_id, review)
        return redirect(url_for('review_pull_request', repository_id=repository_id, pr_id=pr_id))
    except Exception as e:
        traceback.print_exc()
        return f"Error sending review: {type(e).__name__} - {str(e)}", 500


@app.route('/approve/<repository_id>/<int:pr_id>', methods=['POST'])
def approve_pull_request(repository_id, pr_id):
    pat = session.get('pat')
    org_url = session.get('org_url')
    project = session.get('project')
    if not all([pat, org_url, project]):
        return redirect(url_for('index'))
        return
    devops_service = AzureDevOpsService(pat, org_url, project)
    try:

        devops_service.update_pull_request_status(repository_id, pr_id, 1)
        return redirect(url_for('list_pull_requests_get'))
    except Exception as e:
        traceback.print_exc()
        return f"Error approving PR: {type(e).__name__} - {str(e)}", 500

@app.route('/reject/<repository_id>/<int:pr_id>', methods=['POST'])
def reject_pull_request(repository_id, pr_id):
    pat = session.get('pat')
    org_url = session.get('org_url')
    project = session.get('project')
    if not all([pat, org_url, project]):
        return redirect(url_for('index'))
        return
    devops_service = AzureDevOpsService(pat, org_url, project)
    try:
        devops_service.update_pull_request_status(repository_id, pr_id, 3)
        return redirect(url_for('list_pull_requests_get'))
    except Exception as e:
        traceback.print_exc()
        return f"Error rejecting PR: {type(e).__name__} - {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False)