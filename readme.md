# Azure DevOps AI-Powered Pull Request Reviewer

An AI-powered tool that helps streamline the code review process in Azure DevOps by providing automated code reviews using OpenAI's GPT models.

## Features

- 🤖 AI-powered code review generation
- 🔄 View and manage Azure DevOps pull requests
- 📝 Support for multiple programming languages
- 🌐 Multi-language review support (English, Turkish, Spanish, German, French)
- 💬 Manual commenting capability
- 👍 One-click PR approval/rejection
- 📊 Detailed diff view with syntax highlighting
- 🎨 Clean, responsive Material Design interface

## Prerequisites

- Python 3.8+ (for local installation)
- Docker (for containerized deployment)
- Azure DevOps account with PAT (Personal Access Token)
- OpenAI API key
- Access to Azure DevOps repositories

## Installation

1. Clone the repository:
```bash
git clone https://github.com/codehepta/pull_request_reviewer.git
cd pull_request_reviewer
```
2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Create a `.env` file in the project root:
```env
AZURE_DEVOPS_PAT="your_azure_devops_pat"
AZURE_DEVOPS_ORG="your_organization_url"
AZURE_DEVOPS_PROJECT="your_project_name"
OPENAI_API_KEY="your_openai_api_key"
OPENAI_MODEL="gpt-4"  # or any other OpenAI model
```

## Docker Deployment

As an alternative to local installation, you can use Docker:

1. Build the Docker image:
```bash
docker build -t pull-request-reviewer .
```

2. Run the container:
```bash
docker run -p 5000:5000 \
  -e AZURE_DEVOPS_PAT="your_azure_devops_pat" \
  -e AZURE_DEVOPS_ORG="your_organization_url" \
  -e AZURE_DEVOPS_PROJECT="your_project_name" \
  -e OPENAI_API_KEY="your_openai_api_key" \
  -e OPENAI_MODEL="gpt-4" \
  pull-request-reviewer
```

The application will be available at `http://localhost:5000`

## Configuration

1. Set the Flask environment variables:
```bash
export FLASK_APP=app.py
export FLASK_ENV=development  # for development mode
```
2. Start the Flask application:
```bash
flask run
```
3. Open your browser and navigate to `http://127.0.0.1:5000`

4. On the home page, enter your credentials:
   - Azure DevOps PAT   
   - OpenAI API Key
   - Organization URL
   - Project Name
   - Repository Name (optional)

5. Click "Get Pull Requests" to view your assigned PRs

6. Click on any PR to view:
   - PR details
   - Code changes with syntax highlighting
   - Review options

7. Use the "Generate AI Review" button to get an automated code review

8. Choose the review language from the dropdown menu

9. Add manual comments or send the AI-generated review

10. Approve or reject the PR with one click

## Features in Detail

### Code Diff View
- Syntax highlighting for multiple languages
- Clear indication of additions and deletions
- Collapsible file sections
- Line numbers for both old and new versions

### Review Management
- AI-generated reviews in multiple languages
- Manual comment capability
- One-click approve/reject buttons
- Review history tracking

### User Interface
- Material Design components
- Responsive layout
- Mobile-friendly
- Dark mode support through browser settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Security

Never commit sensitive information like API keys or PATs to the repository. Always use environment variables or configuration files that are properly gitignored.