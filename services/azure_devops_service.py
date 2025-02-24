import requests
import os
from dotenv import load_dotenv
import base64
import logging
from difflib import unified_diff

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AzureDevOpsService:
    def __init__(self, pat=None, org_url=None, project=None):
        self.pat = pat or os.getenv('AZURE_DEVOPS_PAT')
        self.org_url = org_url or os.getenv('AZURE_DEVOPS_ORG')
        self.project = project or os.getenv('AZURE_DEVOPS_PROJECT')
        self.base_url = f"{self.org_url}/_apis"
        self.project_base_url = f"{self.org_url}/{self.project}/_apis"
        self.headers = {
            'Authorization': 'Basic ' + base64.b64encode((':' + self.pat).encode('utf-8')).decode('ascii'),
            'Content-Type': 'application/json'
        }

    def _get(self, endpoint, params=None, project_api=False, return_raw=False):
        base_url = self.project_base_url if project_api else self.base_url
        url = f"{base_url}{endpoint}"
        logger.debug(f"GET request to: {url} with params: {params}")
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            if return_raw:
                return response.content  # Return raw bytes, not decoded text
            else:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def _patch(self, endpoint, data):
        url = f"{self.project_base_url}{endpoint}"
        logger.debug(f"PATCH request to: {url} with data: {data}")
        try:
            response = requests.patch(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def _post(self, endpoint, data, project_api=False): # Added project_api parameter
        base_url = self.project_base_url if project_api else self.base_url # Added base_url
        url = f"{base_url}{endpoint}"
        logger.debug(f"POST request to: {url} with data: {data}")
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def _get_file_content(self, repository_id, commit_id, path):
        """Get file content at specific commit"""
        try:
            response = self._get(
                f"/git/repositories/{repository_id}/items",
                params={
                    'api-version': '7.0',
                    'versionType': 'commit',
                    'version': commit_id,
                    'path': path,
                    '$format': 'text'
                },
                project_api=True,
                return_raw=True
            )
            return response.decode('utf-8') if response else None
        except Exception as e:
            logger.error(f"Error getting file content for {path} at {commit_id}: {str(e)}")
            return None

    def _get_content(self, repository_id, commit_id, path):
        """Fetches the content of a file at a specific commit."""
        try:
            # Use return_raw=True to get the raw content
            response = self._get(f"/git/repositories/{repository_id}/items", params={
                "api-version": "7.0",
                "versionType": "commit",
                "version": commit_id,  # Use commitId directly
                "path": path,
                "$format": "text"  # Request plain text format

            }, project_api=True, return_raw=True)  # Get raw content
            return response.decode('utf-8') # Explicitly decode as UTF-8


        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch content for {path} at commit {commit_id}: {e}")
            return ""

    def get_assigned_pull_requests(self):
        try:
            connection_data = self._get("/connectionData")
            user_id = connection_data['authenticatedUser']['id']
            prs = self._get("/git/pullrequests", params={
                "api-version": "7.0",
                "searchCriteria.reviewerId": user_id,
                "searchCriteria.status": "active"
            }, project_api=True)
            return prs['value']
        except Exception as e:
            logger.error(f"Error in get_assigned_pull_requests: {e}")
            raise

    def get_pull_request_details(self, repository_id, pr_id):
        try:
            return self._get(f"/git/repositories/{repository_id}/pullrequests/{pr_id}", params={"api-version": "7.0"}, project_api=True)
        except Exception as e:
            logger.error(f"Error in get_pull_request_details: {e}")
            raise

    def get_pull_request_diff(self, repository_id, pr_id):
        """Get the diff for a pull request"""
        try:
            # Get PR details
            pr_details = self.get_pull_request_details(repository_id, pr_id)
            if not pr_details:
                logger.error("No PR details found")
                return None

            logger.debug(f"PR Title: {pr_details.get('title')}")
            logger.debug(f"PR Status: {pr_details.get('status')}")
            logger.debug(f"Source Branch: {pr_details.get('sourceRefName')}")
            logger.debug(f"Target Branch: {pr_details.get('targetRefName')}")  # Fixed syntax error here

            # Get all commits in the PR
            commits = self._get(
                f"/git/repositories/{repository_id}/pullrequests/{pr_id}/commits",
                params={'api-version': '7.0'},
                project_api=True
            )
            
            if not commits or 'value' not in commits or not commits['value']:
                logger.error("No commits found")
                return None

            logger.debug(f"Found {len(commits['value'])} commits")
            commit_id = commits['value'][0]['commitId']  # Most recent commit
            
            # Get the first parent commit as base
            first_commit = commits['value'][-1]  # Oldest commit in PR
            logger.debug(f"Using first commit: {first_commit['commitId']}")
            
            # Get first commit details to get its parent
            commit_details = self._get(
                f"/git/repositories/{repository_id}/commits/{first_commit['commitId']}",
                params={'api-version': '7.0'},
                project_api=True
            )
            
            base_commit = commit_details.get('parents', [None])[0]
            logger.debug(f"Using base commit: {base_commit}")

            all_changes = []
            processed_files = set()

            # Process each commit
            for commit in commits['value']:
                commit_id = commit['commitId']
                logger.debug(f"Processing commit: {commit_id}")

                # Get changes for this commit
                changes = self._get(
                    f"/git/repositories/{repository_id}/commits/{commit_id}/changes",
                    params={'api-version': '7.0'},
                    project_api=True
                )

                if not changes or 'changes' not in changes:
                    continue

                # Process each changed file
                for change in changes['changes']:
                    if 'item' not in change or change['item'].get('isFolder', False):
                        continue

                    file_path = change['item']['path']
                    if file_path in processed_files:
                        continue

                    processed_files.add(file_path)
                    logger.debug(f"Processing file: {file_path}")

                    try:
                        # Get old version using parent commit
                        old_content = self._get_file_content(
                            repository_id,
                            base_commit,
                            file_path
                        ) if base_commit else None

                        # Get new version using current commit
                        new_content = self._get_file_content(
                            repository_id,
                            commit_id,
                            file_path
                        )

                        if old_content is None and new_content:
                            # New file added
                            old_content = ""
                        elif new_content is None and old_content:
                            # File deleted
                            new_content = ""
                        
                        if old_content is not None and new_content is not None:
                            logger.debug(f"Generating diff for {file_path}")
                            logger.debug(f"Old content size: {len(old_content)}")
                            logger.debug(f"New content size: {len(new_content)}")
                            
                            diff = list(unified_diff(
                                old_content.splitlines(keepends=True),
                                new_content.splitlines(keepends=True),
                                fromfile=f'a/{file_path}',
                                tofile=f'b/{file_path}'
                            ))
                            
                            if diff:
                                all_changes.extend(diff)
                                logger.debug(f"Added {len(diff)} diff lines")

                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")
                        continue

            final_diff = ''.join(all_changes) if all_changes else None
            logger.debug(f"Final diff size: {len(final_diff) if final_diff else 0}")
            return final_diff

        except Exception as e:
            logger.error(f"Error in get_pull_request_diff: {str(e)}")
            logger.exception("Full traceback:")
            return None

    def get_file_content(self, repository_id, version, path):
        """Get file content at specific version"""
        try:
            url = f"{self.base_url}/{self.project}/_apis/git/repositories/{repository_id}/items"
            params = {
                'api-version': '7.0',
                'versionType': 'commit',
                'version': version,
                'path': path,
                '$format': 'text'
            }
            response = self._get(url, params=params)
            return response if isinstance(response, str) else None
        except Exception as e:
            logging.error(f"Error getting file content: {str(e)}")
            return None

    def update_pull_request_status(self, repository_id, pr_id, status):
        """Updates the PR status.  Status: 1 = Approved, 3 = Rejected"""
        data = {
            "status": status
        }
        return self._patch(f"/git/repositories/{repository_id}/pullrequests/{pr_id}", data=data, params={"api-version": "7.0"})
    def create_pull_request_comment(self, repository_id, pr_id, comment):
        """Creates a comment on a pull request."""
        data = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": comment,
                    "commentType": "text"
                }
            ],
            "status": 1
        }
        return self._post(f"/git/repositories/{repository_id}/pullrequests/{pr_id}/threads?api-version=7.0", data=data, project_api=True)