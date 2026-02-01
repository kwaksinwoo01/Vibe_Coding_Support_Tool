# GitHub Actions Workflow Documentation

## Poll and Process Workflow

The `poll-and-process.yml` workflow automates the detection of Dropbox file changes and communication with the domain service.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│         GitHub Actions (Every Minute, Mon-Fri)           │
│                                                          │
│  1. Run main.py --time 15m                              │
│  2. Parse log output                                    │
│  3. Extract file information                            │
│  4. POST each file to domain /enqueue                   │
│  5. Upload results as artifact                          │
└─────────────────────────────────────────────────────────┘
```

## Schedule

The workflow runs automatically:

- **Working Hours (KST 08:00-19:00)**: Every minute
- **Days**: Monday to Friday only (excludes weekends)
- **Off Hours**: Does not run

### Cron Schedule

```yaml
schedule:
  # UTC 23:00-23:59 Mon-Fri (KST 08:00-08:59)
  - cron: '0-59 23 * * 1-5'
  
  # UTC 00:00-09:59 Mon-Fri (KST 09:00-18:59)
  - cron: '0-59 0-9 * * 1-5'
  
  # UTC 10:00-10:59 Mon-Fri (KST 19:00-19:59)
  - cron: '0-59 10 * * 1-5'
```

## Manual Trigger

You can trigger the workflow manually:

1. Go to Actions tab in GitHub
2. Select "Poll and Process Dropbox Files"
3. Click "Run workflow"
4. Configure options:
   - **time_range**: Time range to process (default: 15m)
   - **dry_run**: Run without making changes (default: false)

## Required Secrets

Configure these secrets in your repository settings (Settings → Secrets → Actions):

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DROPBOX_CLIENT_ID` | Dropbox app client ID | `abc123xyz789` |
| `DROPBOX_CLIENT_SECRET` | Dropbox app client secret | `secret123` |
| `DROPBOX_REFRESH_TOKEN` | OAuth refresh token | `token456` |
| `DROPBOX_ADMIN_USER_ID` | Admin user ID for Dropbox | `dbid:AAH...` |
| `DROPBOX_TEMPLATE_ID` | Metadata template ID | `template789` |
| `WEBHOOK_URL` | Domain service URL | `https://your-domain.run.app` |
| `WORKFLOW_SHARED_SECRET` | Authentication token for domain | `shared-secret-abc` |

## Workflow Steps

### 1. Checkout Repository

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
```

Clones the repository code.

### 2. Setup Python

```yaml
- name: Set up Python 3.12
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```

Installs Python 3.12 with pip caching for faster builds.

### 3. Install Dependencies

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
```

Installs required Python packages.

### 4. Create .env File

```yaml
- name: Create .env file
  run: |
    cat > .env << EOF
    DROPBOX_CLIENT_ID=${{ secrets.DROPBOX_CLIENT_ID }}
    DROPBOX_CLIENT_SECRET=${{ secrets.DROPBOX_CLIENT_SECRET }}
    # ... other secrets ...
    EOF
```

Creates environment file from GitHub secrets.

### 5. Poll Dropbox

```yaml
- name: Poll Dropbox and detect changes
  id: poll_dropbox
  run: |
    python main.py --time "${TIME_RANGE}" > poll_results.log 2>&1
    PROCESSED_COUNT=$(grep -c "📄 시간 범위 내 파일:" poll_results.log || echo "0")
    echo "processed_count=${PROCESSED_COUNT}" >> $GITHUB_OUTPUT
```

Runs main.py to detect file changes and counts processed files.

### 6. Send to Domain

```yaml
- name: Send results to domain
  if: steps.poll_dropbox.outputs.processed_count != '0'
  run: |
    # Parse log and extract files
    # For each file, POST to domain /enqueue
```

Sends detected files to the domain service queue.

### 7. Upload Artifacts

```yaml
- name: Upload poll results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: poll-results-${{ github.run_id }}
    path: poll_results.log
    retention-days: 7
```

Uploads logs for debugging (retained for 7 days).

### 8. Create Summary

```yaml
- name: Summary
  if: always()
  run: |
    echo "## Workflow Summary" >> $GITHUB_STEP_SUMMARY
    # ... add summary information ...
```

Creates a workflow summary visible in GitHub UI.

## Output Format

### Log File Structure

The workflow generates `poll_results.log`:

```
🔍 Polling Dropbox for file changes (time range: 15m)...
📄 시간 범위 내 파일: /Business/Uploads/file1.pdf
   업로더: John Doe (john@example.com)
   파일 ID: id:abc123
   시간: 2025-01-15 14:30:00 KST
📄 시간 범위 내 파일: /Business/Uploads/file2.jpg
   업로더: Jane Smith (jane@example.com)
   파일 ID: id:xyz789
   시간: 2025-01-15 14:35:00 KST
✅ Polling completed. Found 2 files.
```


## Monitoring

### Check Workflow Status

1. Go to repository Actions tab
2. View recent runs
3. Click on a run to see details

### View Logs

1. Click on workflow run
2. Expand each step to view logs
3. Download artifacts for detailed logs

### Debug Failed Runs

If workflow fails:

1. Check step that failed (red X)
2. View error messages in logs
3. Download `poll_results.log` artifact
4. Check secrets are configured correctly

## Customization

### Change Schedule

Edit the cron expressions in `poll-and-process.yml`:

```yaml
on:
  schedule:
    # Run every 5 minutes instead of every minute
    - cron: '*/5 * * * *'
```

### Change Time Range

Modify the default time range (adjust based on polling frequency):

```yaml
env:
  # For 1-minute polling, use 15m-30m range
  TIME_RANGE: ${{ github.event.inputs.time_range || '15m' }}
  
  # For less frequent polling (5min), use 30m-1h range
  TIME_RANGE: ${{ github.event.inputs.time_range || '30m' }}
```

### Add Custom Processing

Add steps after polling:

```yaml
- name: Custom processing
  run: |
    # Your custom code here
    python custom_script.py
```

### Filter Files

Add filtering logic in "Send to domain" step:

```yaml
- name: Send results to domain
  run: |
    while IFS= read -r line; do
      if [[ "$line" =~ "📄 시간 범위 내 파일: "(.+) ]]; then
        FILE_PATH="${BASH_REMATCH[1]}"
        
        # Filter: only send PDF files
        if [[ "$FILE_PATH" == *.pdf ]]; then
          # Send to domain
          curl -X POST ...
        fi
      fi
    done < poll_results.log
```

## Troubleshooting

### Workflow Not Running

**Problem**: Workflow doesn't trigger on schedule

**Solutions**:

1. Check cron syntax is correct
2. Verify repository is active (not archived)
3. Check GitHub Actions is enabled
4. Ensure workflow file is in `.github/workflows/`

### Authentication Errors

**Problem**: 401 or 403 errors when calling domain

**Solutions**:
1. Verify `WORKFLOW_SHARED_SECRET` is set correctly
2. Check domain service accepts the token
3. Ensure header `X-Workflow-Token` is sent

### No Files Detected

**Problem**: Workflow runs but finds no files

**Solutions**:
1. Check time range matches polling frequency (15m for 1-min polling)
2. Verify Dropbox credentials are valid
3. Run `main.py --time 15m` locally to test
4. Check file activity in Dropbox

### Timeout Issues

**Problem**: Workflow times out (default: 5 minutes)

**Solutions**:
1. Increase timeout in workflow:
   ```yaml
   jobs:
     poll-and-process:
       timeout-minutes: 10
   ```
2. Reduce time range to process fewer files
3. Optimize main.py performance

## Best Practices

### 1. Limit API Calls

Don't poll too frequently:
- Every minute during working hours is reasonable
- Consider every 5 minutes if system load is high
- **Weekend exclusion**: Workflow automatically skips Saturdays and Sundays to save resources

### 2. Match Time Range to Polling Frequency

Time range should be proportional to polling interval:
- **1-minute polling**: Use 15m time range (as configured)
- **5-minute polling**: Use 30m-1h time range
- **Hourly polling**: Use 2h-4h time range

This prevents:
- Processing the same files multiple times
- Unnecessary API calls
- Increased processing time

### 3. Monitor Costs

GitHub Actions usage:
- Free tier: 2,000 minutes/month for private repos
- Check usage in Settings → Billing

### 4. Handle Errors Gracefully

Add error handling:
```yaml
- name: Poll Dropbox
  continue-on-error: true  # Don't fail entire workflow
```

### 5. Use Secrets Properly

- Never hardcode credentials
- Use GitHub secrets for sensitive data
- Rotate secrets periodically

### 6. Log Appropriately

- Include timestamps
- Log both successes and failures
- Use structured logging for parsing

## Integration with Domain Service

The workflow integrates with the domain service:

```
Workflow → POST /enqueue → Domain Service
                             │
                             ├─> tasks.json (GCS)
                             │
                             └─> Client polls ← GET /tasks
```

### Domain Endpoints

- **POST /enqueue**: Add task to queue
  - Auth: `X-Workflow-Token: <secret>`
  - Body: Task payload
  
- **GET /tasks**: List pending tasks
  - Auth: `X-Client-Token: <token>`
  - Query: `?limit=20`

- **POST /tasks/ack**: Update task status
  - Auth: `X-Client-Token: <token>`
  - Body: `{ids: [...], action: "start|done|cancel"}`

## Examples

### Example 1: Manual Trigger with Custom Time

```bash
# Using GitHub CLI
gh workflow run poll-and-process.yml \
  -f time_range=6h \
  -f dry_run=false
```

### Example 2: Check Recent Runs

```bash
# List recent runs
gh run list --workflow=poll-and-process.yml --limit 10

# View specific run
gh run view 123456789

# Download artifacts
gh run download 123456789
```

### Example 3: Debug Locally

```bash
# Simulate workflow locally
export DROPBOX_CLIENT_ID="your-id"
export DROPBOX_CLIENT_SECRET="your-secret"
# ... set other env vars ...

# Run main.py with 15m time range (matches workflow)
python main.py --time 15m > poll_results.log 2>&1

# Check results
grep "📄 시간 범위 내 파일:" poll_results.log

# Test domain call
BODY='{"job_type":"test","data":{}}'
curl -X POST "$WEBHOOK_URL/enqueue" \
  -H "Content-Type: application/json" \
  -H "X-Workflow-Token: $WORKFLOW_SHARED_SECRET" \
  -d "$BODY"
```

## See Also

- [Main.py Documentation](../README.md)
- [Domain Service Documentation](../github-webhook-function/README.md)
- [Client OAuth Guide](../oauth/CLIENT_OAUTH_GUIDE.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
