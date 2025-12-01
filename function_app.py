import azure.functions as func
import logging
import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import slack as slack_integration

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import heavy dependencies after basic setup
try:
    import requests
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.devcenter import DevCenterMgmtClient
    from azure.developer.devcenter import DevCenterClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.core.rest import HttpRequest
    logger.info("Successfully imported all Azure dependencies")
except Exception as e:
    logger.error(f"Failed to import dependencies: {e}", exc_info=True)
    raise

app = func.FunctionApp()
logger.info("Function app initialized")


def get_credential():
    """Get Azure credential for authentication."""
    return DefaultAzureCredential()


def fetch_all_dev_centers_and_projects(mgmt_client) -> List[Dict]:
    """
    Fetch all DevCenter projects using the DevCenter management client.
    Returns list of dicts with 'project_name', 'resource_group', 'devcenter_name', 'devcenter_uri'.
    """
    logger.info("Fetching all DevCenter projects using management client...")
    
    projects_info = []
    
    try:
        # List all DevCenters in the subscription
        devcenters = list(mgmt_client.dev_centers.list_by_subscription())
        logger.info(f"Found {len(devcenters)} DevCenters")
        
        # For each DevCenter, list its projects
        for devcenter in devcenters:
            devcenter_name = devcenter.name
            devcenter_rg = devcenter.id.split('/')[4]  # Extract resource group from resource ID
            devcenter_uri = devcenter.dev_center_uri
            
            logger.info(f"Fetching projects for DevCenter '{devcenter_name}' in RG '{devcenter_rg}'...")
            
            try:
                # List projects for this DevCenter
                projects = list(mgmt_client.projects.list_by_resource_group(devcenter_rg))
                
                for project in projects:
                    # Verify this project belongs to this DevCenter
                    if hasattr(project, 'dev_center_id') and devcenter.id.lower() in project.dev_center_id.lower():
                        projects_info.append({
                            'project_name': project.name,
                            'resource_group': devcenter_rg,
                            'devcenter_name': devcenter_name,
                            'devcenter_uri': devcenter_uri
                        })
                        logger.info(f"  - Found project: {project.name}")
            
            except Exception as e:
                logger.error(f"Error fetching projects for DevCenter '{devcenter_name}': {str(e)}", exc_info=True)
                continue
        
        logger.info(f"Total projects found: {len(projects_info)}")
        return projects_info
    
    except Exception as e:
        logger.error(f"Error fetching DevCenters: {str(e)}", exc_info=True)
        return []


def fetch_environments_from_project(credential, devcenter_endpoint: str, project_name: str) -> List[Dict]:
    """
    Fetch all environments from a specific DevCenter project using the data plane API.
    Returns list of environment dictionaries with properties including expiration date.
    """
    try:
        logger.info(f"Fetching environments from project '{project_name}' via endpoint '{devcenter_endpoint}'...")
        logger.info(f"Creating DevCenterClient with endpoint: {devcenter_endpoint}")
        
        # Create data plane client with DevCenter endpoint
        devcenter_client = DevCenterClient(endpoint=devcenter_endpoint, credential=credential)
        
        # List all environments in the project
        environments = []
        
        try:
            # Use DevCenterClient's internal pipeline to make REST API calls
            logger.info(f"Fetching environments via DevCenterClient pipeline for project '{project_name}'...")
            
            try:
                # Use the SDK's send_request method which handles auth properly
                relative_url = f"/projects/{project_name}/environments?api-version=2025-02-01"
                print(f"🔧 DEBUG: Making request to: {relative_url}")
                
                request = HttpRequest(
                    method="GET",
                    url=relative_url
                )
                
                print(f"� DEBUG: Sending request through DevCenterClient pipeline...")
                response = devcenter_client.send_request(request)
                response.raise_for_status()
                
                page = response.json()
                logger.info(f"✅ DEBUG: Successfully got response via SDK pipeline")
                logger.info(f"📊 DEBUG: Response has {len(page.get('value', []))} environments")
                
                env_count = 0
                url = page.get("nextLink")  # For pagination
                
                logger.info(f"next page link: {url}")

                for env in page.get("value", []):
                    env_count += 1
                    env_name = env.get("name", "unknown")
                    logger.info(f"  Processing environment #{env_count}: {env_name}")
                    
                    # Print raw environment data for debugging
                    logger.info(f"\n{'='*80}")
                    logger.info(f"DEBUG: Environment #{env_count} - {env_name}")
                    logger.info(f"{'='*80}")
                    logger.info(f"Raw JSON keys: {list(env.keys())}")
                    logger.info(f"Full JSON: {json.dumps(env, indent=2, default=str)}")
                    logger.info(f"{'='*80}\n")
                    
                    expiration_from_api = env.get("expirationDate")
                    logger.info(f"🔍 DEBUG: Raw expirationDate from API = '{expiration_from_api}' (type: {type(expiration_from_api)})")
                    
                    env_dict = {
                        'name': env.get("name"),
                        'project_name': project_name,
                        'catalogName': env.get("catalogName"),
                        'environmentDefinitionName': env.get("environmentDefinitionName"),
                        'environmentType': env.get("environmentType"),
                        'user': env.get("user"),
                        'provisioningState': env.get("provisioningState"),
                        'resourceGroupId': env.get("resourceGroupId"),
                        'expirationDate': expiration_from_api
                    }
                    
                    logger.info(f"✅ DEBUG: env_dict created with expirationDate = '{env_dict['expirationDate']}'")
                    logger.info(f"📦 DEBUG: About to append to environments list")
                    environments.append(env_dict)
                    logger.info(f"✔️  DEBUG: Successfully appended. Total envs now: {len(environments)}")
                
                # Handle pagination
                while url:
                    logger.info(f"🔄 DEBUG: Following nextLink for pagination...")
                    next_request = HttpRequest(method="GET", url=url)
                    response = devcenter_client.send_request(next_request)
                    response.raise_for_status()
                    page = response.json()
                    
                    for env in page.get("value", []):
                        env_count += 1
                        env_name = env.get("name", "unknown")
                        logger.info(f"  Processing environment #{env_count}: {env_name}")
                        
                        expiration_from_api = env.get("expirationDate")
                        logger.info(f"🔍 DEBUG: Raw expirationDate from API = '{expiration_from_api}' (type: {type(expiration_from_api)})")
                        
                        env_dict = {
                            'name': env.get("name"),
                            'project_name': project_name,
                            'catalogName': env.get("catalogName"),
                            'environmentDefinitionName': env.get("environmentDefinitionName"),
                            'environmentType': env.get("environmentType"),
                            'user': env.get("user"),
                            'provisioningState': env.get("provisioningState"),
                            'resourceGroupId': env.get("resourceGroupId"),
                            'expirationDate': expiration_from_api
                        }
                        
                        environments.append(env_dict)
                    
                    url = page.get("nextLink")
            
            except requests.exceptions.HTTPError as http_err:
                if http_err.response.status_code == 403:
                    logger.error(f"❌ 403 Forbidden when calling REST API")
                    logger.error(f"URL: {http_err.response.url}")
                    logger.error(f"Response body: {http_err.response.text}")
                    logger.error(f"Response headers: {dict(http_err.response.headers)}")
                    logger.warning(f"Credentials may not have 'Deployment Environments Reader' role")
                    logger.warning(f"Managed Identity needs 'Deployment Environments Reader' role on the DevCenter project")
                    logger.info(f"Falling back to SDK (which may not have expirationDate)...")
                    
                    # Fallback to SDK approach
                    paged_envs = devcenter_client.list_all_environments(project_name=project_name)
                    env_count = 0
                    for env in paged_envs:
                        env_count += 1
                        logger.info(f"  Processing environment #{env_count}: {env.name if hasattr(env, 'name') else 'unknown'}")
                        
                        # Try multiple attribute names for expiration
                        expiration_value = None
                        for attr in ['expiration_date', 'expirationDate', 'expiration']:
                            if hasattr(env, attr):
                                expiration_value = getattr(env, attr)
                                if expiration_value:
                                    break
                        
                        env_dict = {
                            'name': env.name if hasattr(env, 'name') else None,
                            'project_name': project_name,
                            'catalogName': env.catalog_name if hasattr(env, 'catalog_name') else None,
                            'environmentDefinitionName': env.environment_definition_name if hasattr(env, 'environment_definition_name') else None,
                            'environmentType': env.environment_type if hasattr(env, 'environment_type') else None,
                            'user': env.user if hasattr(env, 'user') else None,
                            'provisioningState': env.provisioning_state if hasattr(env, 'provisioning_state') else None,
                            'resourceGroupId': env.resource_group_id if hasattr(env, 'resource_group_id') else None,
                            'expirationDate': expiration_value
                        }
                        environments.append(env_dict)
                else:
                    raise
            

        except AttributeError as ae:
            logger.error(f"API method not available: {str(ae)}")
            # Alternative: try listing environments by user
            logger.info("Attempting to list environments using alternative API...")
            try:
                # List environments for "me" (the service principal/managed identity)
                paged_envs = devcenter_client.list_environments(project_name=project_name)
                for env in paged_envs:
                    logger.info(f"  Found environment: {env.name if hasattr(env, 'name') else 'unknown'}")
                    env_dict = {
                        'name': env.name if hasattr(env, 'name') else None,
                        'project_name': project_name,
                        'catalogName': env.catalog_name if hasattr(env, 'catalog_name') else None,
                        'environmentDefinitionName': env.environment_definition_name if hasattr(env, 'environment_definition_name') else None,
                        'environmentType': env.environment_type if hasattr(env, 'environment_type') else None,
                        'user': env.user if hasattr(env, 'user') else None,
                        'provisioningState': env.provisioning_state if hasattr(env, 'provisioning_state') else None,
                        'resourceGroupId': env.resource_group_id if hasattr(env, 'resource_group_id') else None,
                        'expirationDate': env.expiration_date if hasattr(env, 'expiration_date') else None
                    }
                    environments.append(env_dict)
            except Exception as inner_e:
                logger.error(f"Alternative API also failed: {str(inner_e)}", exc_info=True)
        
        logger.info(f"Found {len(environments)} environments in project '{project_name}'")
        return environments
    
    except Exception as e:
        logger.error(f"Error fetching environments from project '{project_name}': {str(e)}", exc_info=True)
        return []


def fetch_resource_group_tags(credential, subscription_id: str, rg_name: str) -> Dict[str, str]:
    """
    Fetch tags from a resource group.
    Returns dictionary of tags, or empty dict on error.
    """
    try:
        resource_client = ResourceManagementClient(credential, subscription_id)
        rg = resource_client.resource_groups.get(rg_name)
        return rg.tags or {}
    except Exception as e:
        logger.warning(f"Could not fetch tags for resource group '{rg_name}': {str(e)}")
        return {}


def fetch_all_environments() -> List[Dict]:
    """
    Fetch all Azure Deployment Environments using DevCenter management and data plane APIs.
    
    Steps:
    1. Use DevCenterMgmtClient to list all DevCenters and their projects
    2. For each project, use DevCenterClient (data plane) to list environments
    3. Extract expiration dates from environment objects
    4. Correlate with resource groups to get owner tags
    5. Return enriched environment list
    """
    logger.info("Fetching all Azure Deployment Environments via DevCenter API...")
    
    credential = get_credential()
    subscription_id = os.environ.get("ADE_SUBSCRIPTION_ID")
    logger.info(f"🔑 Subscription ID: {subscription_id}")
    
    if not subscription_id:
        raise ValueError("Missing required environment variable: ADE_SUBSCRIPTION_ID")
    
    # Step 1: Get all DevCenter projects using management client
    logger.info(f"REACHING DEVCENTER MGMT CLIENT NOW")
    logger.info(f"🔐 Credential type: {type(credential).__name__}")
    logger.info(f"🔐 Credential object: {credential}")
    mgmt_client = DevCenterMgmtClient(credential, subscription_id)
    projects = fetch_all_dev_centers_and_projects(mgmt_client)
    
    if not projects:
        logger.warning("No DevCenter projects found in subscription")
        return []
    
    all_environments = []
    
    # Step 2: For each project, fetch environments using data plane API
    for project_info in projects:
        project_name = project_info.get('project_name')
        devcenter_uri = project_info.get('devcenter_uri')
        
        if not project_name or not devcenter_uri:
            logger.warning(f"Skipping project with missing info: {project_info}")
            continue
        
        logger.info(f"Processing project '{project_name}' with DevCenter URI '{devcenter_uri}'...")
        
        # Fetch environments from this project using data plane API
        envs = fetch_environments_from_project(credential, devcenter_uri, project_name)
        print(f"🔄 DEBUG: fetch_environments_from_project returned {len(envs)} environments")
        
        # Step 3: Correlate with resource groups to get owner tags
        for env in envs:
            env_name = env.get('name')
            exp_before = env.get('expirationDate')
            print(f"🔄 DEBUG: Processing env '{env_name}' - expirationDate BEFORE tagging: '{exp_before}'")
            
            # Derive resource group name from resourceGroupId if available
            rg_id = env.get('resourceGroupId')
            if rg_id:
                # Extract RG name from ID: /subscriptions/.../resourceGroups/<name>
                rg_name = rg_id.split('/')[-1] if '/' in rg_id else None
            else:
                # Fallback: assume {projectName}-{environmentName} pattern
                rg_name = f"{project_name}-{env_name}"
            
            if rg_name:
                # Fetch tags from the environment's resource group
                rg_tags = fetch_resource_group_tags(credential, subscription_id, rg_name)
                env['environment_resource_group'] = rg_name
                env['tags'] = rg_tags
            
            exp_after = env.get('expirationDate')
            print(f"➕ DEBUG: About to append env '{env_name}' - expirationDate AFTER tagging: '{exp_after}'")
            all_environments.append(env)
            print(f"✅ DEBUG: Appended. Total all_environments: {len(all_environments)}")
    
    logger.info(f"Found total of {len(all_environments)} Azure Deployment Environments across all projects")
    return all_environments


def extract_owner_email(env: Dict) -> Optional[str]:
    """
    Extract owner email from environment.
    Priority: 
    1. Resource group tags (created_by, owner, etc.) - most likely to have email
    2. Environment 'user' field - AAD object ID from DevCenter API
    """
    # Try resource group tags first
    tags = env.get('tags', {})
    if tags:
        for key, value in tags.items():
            if key.lower() in ('created_by', 'createdby', 'created-by', 'owner', 'user-email'):
                return value
    
    # Fall back to user field from DevCenter API (AAD object ID)
    user = env.get('user')
    if user:
        return user
    
    return None


def parse_expiration_date(expiration_str: Optional[str]) -> Optional[datetime]:
    """Parse expiration date from ISO format string or date string."""
    if not expiration_str:
        logger.info(f"[PARSE] No expiration string provided")
        return None
    
    logger.info(f"[PARSE] Parsing expiration string: '{expiration_str}' (type: {type(expiration_str).__name__})")
    
    try:
        if expiration_str.endswith('Z'):
            result = datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
            logger.info(f"[PARSE] Parsed as ISO with Z suffix: {result}")
            return result
        
        if 'T' in expiration_str:
            dt = datetime.fromisoformat(expiration_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            logger.info(f"[PARSE] Parsed as ISO datetime: {dt}")
            return dt
        
        dt = datetime.strptime(expiration_str, '%Y-%m-%d')
        result = dt.replace(tzinfo=timezone.utc)
        logger.info(f"[PARSE] Parsed as date only: {result}")
        return result
        
    except Exception as e:
        logger.warning(f"[PARSE] Failed to parse date '{expiration_str}': {e}")
        return None


def categorize_by_expiration(environments: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize environments by expiration timeframes."""
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    three_days = now + timedelta(days=3)
    seven_days = now + timedelta(days=7)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"[CATEGORIZE] Current time (UTC): {now}")
    logger.info(f"[CATEGORIZE] Tomorrow threshold: {tomorrow}")
    logger.info(f"[CATEGORIZE] 3-day threshold: {three_days}")
    logger.info(f"[CATEGORIZE] 7-day threshold: {seven_days}")
    logger.info(f"[CATEGORIZE] Total environments to process: {len(environments)}")
    logger.info(f"{'='*60}\n")
    
    categories = {
        'expired': [],
        'tomorrow': [],
        '3_days': [],
        '7_days': [],
        'future': []
    }
    
    for idx, env in enumerate(environments, 1):
        env_name = env.get('name', 'UNKNOWN')
        logger.info(f"\n--- Processing Environment #{idx}: {env_name} ---")
        
        # Get expiration date from top level (from DevCenter API)
        expiration_value = env.get('expirationDate')
        print(f"DEBUG: expiration_value = {expiration_value}, type = {type(expiration_value)}")
        
        if not expiration_value:
            logger.info(f"[CATEGORIZE] Environment '{env_name}' has NO expiration date - SKIPPING")
            continue
        
        logger.info(f"[CATEGORIZE] Raw expiration value: {expiration_value} (type: {type(expiration_value).__name__})")
        
        # Convert datetime object to string if needed, or parse if string
        if isinstance(expiration_value, datetime):
            expiration_date = expiration_value
            logger.info(f"[CATEGORIZE] Value is already datetime object: {expiration_date}")
        else:
            logger.info(f"[CATEGORIZE] Value is string, calling parse_expiration_date...")
            expiration_date = parse_expiration_date(expiration_value)
        
        if not expiration_date:
            logger.warning(f"[CATEGORIZE] Could not parse expiration date for '{env_name}': {expiration_value} - SKIPPING")
            continue
        
        # Get owner using the updated extract_owner_email function
        owner_email = extract_owner_email(env)
        logger.info(f"[CATEGORIZE] Owner email: {owner_email}")
        
        # Calculate days until expiration
        time_diff = expiration_date - now
        days_until_expiration = time_diff.days
        hours_until_expiration = time_diff.total_seconds() / 3600
        
        logger.info(f"[CATEGORIZE] Expiration date: {expiration_date}")
        logger.info(f"[CATEGORIZE] Time difference: {time_diff}")
        logger.info(f"[CATEGORIZE] Days until expiration: {days_until_expiration}")
        logger.info(f"[CATEGORIZE] Hours until expiration: {hours_until_expiration:.2f}")
        
        env_info = {
            "name": env.get("name"),
            "owner_email": owner_email or "unknown",
            "expirationDate": expiration_date.isoformat(),
            "daysUntilExpiration": days_until_expiration,
            "projectName": env.get("project_name"),
            "environmentResourceGroup": env.get("environment_resource_group"),
            "environmentDefinition": env.get("environmentDefinitionName"),
            "catalogName": env.get("catalogName"),
            "provisioningState": env.get("provisioningState"),
            "resourceId": env.get("resourceGroupId")
        }
        
        # Determine category with detailed logging
        if expiration_date < now:
            logger.info(f"[CATEGORIZE] ❌ EXPIRED (expiration {expiration_date} < now {now})")
            categories['expired'].append(env_info)
        elif expiration_date <= tomorrow:
            logger.info(f"[CATEGORIZE] 🚨 EXPIRES TOMORROW (expiration {expiration_date} <= tomorrow {tomorrow})")
            categories['tomorrow'].append(env_info)
        elif expiration_date <= three_days:
            logger.info(f"[CATEGORIZE] ⚠️  EXPIRES IN 3 DAYS (expiration {expiration_date} <= 3-days {three_days})")
            categories['3_days'].append(env_info)
        elif expiration_date <= seven_days:
            logger.info(f"[CATEGORIZE] ⏰ EXPIRES IN 7 DAYS (expiration {expiration_date} <= 7-days {seven_days})")
            categories['7_days'].append(env_info)
        else:
            logger.info(f"[CATEGORIZE] ✅ FUTURE (expiration {expiration_date} > 7-days {seven_days})")
            categories['future'].append(env_info)
    
    return categories


def check_expiring_environments() -> Tuple[Dict[str, List[Dict]], int]:
    """Check all environments and categorize by expiration timeframes."""
    environments = fetch_all_environments()
    categorized = categorize_by_expiration(environments)
    
    total_attention = (
        len(categorized['expired']) +
        len(categorized['tomorrow']) +
        len(categorized['3_days']) +
        len(categorized['7_days'])
    )
    
    logger.info(f"Summary: {len(categorized['expired'])} expired, "
                f"{len(categorized['tomorrow'])} tomorrow, "
                f"{len(categorized['3_days'])} in 3 days, "
                f"{len(categorized['7_days'])} in 7 days")
    
    return categorized, total_attention


def send_personal_slack_notification(env: Dict[str, List[Dict]]) -> bool:
# struct is category [expired, tomorrow, 3_days, 7_days] ->
#  env_details [ 
#       name, owner_email, expirationDate, daysUntilExpiration, projectName, environmentResourceGroup, 
#       environmentDefinition, catalogName, provisioningState, resourceId 
# ]
    """Send personal Slack notification to environment owner about expiration."""
    for category in env:
        logger.info(f"Sending personal Slack notifications for category: {category}")
        for environment in env[category]:
            owner_email = environment.get("owner_email")
            if not owner_email or "unknown" in owner_email:
                logger.warning(f"Skipping Slack notification for environment '{environment.get('name')}' due to unknown owner email")
                continue
            
            user_id = slack_integration.get_user_by_email(owner_email)
            if not user_id:
                logger.warning(f"Could not find Slack user ID for email: {owner_email}")
                continue
            
            message = (
                f"Hello! Your Azure Deployment Environment *{environment.get('name')}* is set to expire on "
                f"*{environment.get('expirationDate')[:10]}* (in *{environment.get('daysUntilExpiration')}* days).\n"
                f"Please take necessary action to extend or decommission it.\n\n"
                f"Project: {environment.get('projectName')}\n"
                f"Resource Group: {environment.get('environmentResourceGroup')}\n"
                f"Environment Definition: {environment.get('environmentDefinition')}\n"
                f"Catalog: {environment.get('catalogName')}\n"
                f"Provisioning State: {environment.get('provisioningState')}\n"
                f"Resource ID: {environment.get('resourceId')}"
            )
            
            sent = slack_integration.send_slack_message(user_id, message)
            if sent:
                logger.info(f"Sent Slack notification to {owner_email} for environment '{environment.get('name')}'")
            else:
                logger.error(f"Failed to send Slack notification to {owner_email} for environment '{environment.get('name')}'")


def send_slack_notification(categorized_envs: Dict[str, List[Dict]], total_count: int) -> bool:
    """Send Slack notification about expiring environments."""
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    
    if not channel_id:
        logger.warning("SLACK_CHANNEL_ID not configured")
        return False
    
    mock_mode = os.environ.get("SLACK_MOCK", "0") in ("1", "true", "True")
    
    if total_count == 0:
        message = "✅ All Azure Deployment Environments are healthy - no expiration warnings."
        payload = [{ "type": "section", "text": { "type" : "plain_text", "text": message} }]
    else:
        expired_count = len(categorized_envs['expired'])
        tomorrow_count = len(categorized_envs['tomorrow'])
        three_days_count = len(categorized_envs['3_days'])
        seven_days_count = len(categorized_envs['7_days'])
        
        warning_emoji = "🚨" if expired_count > 0 else "⚠️"
        text = f"{warning_emoji} Azure Deployment Environment Expiration Alert"
        
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{warning_emoji} ADE Expiration Alert", "emoji": True}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Summary:* {total_count} environment(s) need attention\n\n"
                        f"❌ {expired_count} already expired\n"
                        f"🚨 {tomorrow_count} expire tomorrow\n"
                        f"⚠️ {three_days_count} expire in 3 days\n"
                        f"⏰ {seven_days_count} expire in 7 days"
                    )
                }
            },
            {"type": "divider"}
        ]
        
        # Add expired environments
        if expired_count > 0:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*❌ EXPIRED ({expired_count})*"}})
            for env in categorized_envs['expired'][:5]:
                days = abs(env["daysUntilExpiration"])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• `{env['name']}`\n  Owner: {env['owner_email']}\n  Expired: {days} day(s) ago"
                    }
                })
        
        # Add tomorrow's expirations
        if tomorrow_count > 0:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*🚨 TOMORROW ({tomorrow_count})*"}})
            for env in categorized_envs['tomorrow'][:5]:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• `{env['name']}`\n  Owner: {env['owner_email']}\n  Expires: {env['expirationDate'][:10]}"
                    }
                })
        
        # Add 3-day warnings
        if three_days_count > 0:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*⚠️ 3 DAYS ({three_days_count})*"}})
            for env in categorized_envs['3_days'][:3]:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• `{env['name']}`\n  Owner: {env['owner_email']}\n  Days left: {env['daysUntilExpiration']}"
                    }
                })
        
        # Add 7-day warnings
        if seven_days_count > 0:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*⏰ 7 DAYS ({seven_days_count})*"}})
            for env in categorized_envs['7_days'][:3]:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• `{env['name']}`\n  Owner: {env['owner_email']}\n  Days left: {env['daysUntilExpiration']}"
                    }
                })
        
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"🤖 _ADE Expiration Monitor | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
            }]
        })
        
        payload = blocks
    
    if mock_mode:
        logger.info(f"[MOCK] Would send Slack notification")
        logger.info(json.dumps(payload, indent=2))
        return True
    
    try:
        sent = slack_integration.send_slack_message(channel_id,"", payload)
        logger.info("Slack notification sent successfully" if sent else "Failed to send Slack notification")
        return True
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")
        return False


@app.timer_trigger(schedule="0 9 * * *", arg_name="myTimer", run_on_startup=False)
def expirationDateNotice(myTimer: func.TimerRequest) -> None:
    """
    Timer-triggered function that runs daily to check for expiring ADE environments.
    Schedule: Daily at 9:00 AM UTC (cron: 0 9 * * *)
    """
    if myTimer.past_due:
        logger.info('Timer is past due!')
    
    logger.info('ADE Expiration Monitor started')
    
    try:
        categorized_envs, total_count = check_expiring_environments()
        
        logger.info(f"Found {total_count} environment(s) requiring attention")
        
        # send notifications to env owners
        success_personal = send_personal_slack_notification(categorized_envs)

        # send summary notification to monitor channel
        success_channel = send_slack_notification(categorized_envs, total_count)

        if  success_personal and success_channel:
            logger.info("Monitor completed successfully")
        else:
            logger.warning("Monitor completed with warnings")
        
    except Exception as e:
        logger.error(f"Error in expiration check: {str(e)}", exc_info=True)
        
        # Send error notification
        try:
            error_message = f"❌ ADE Expiration Monitor encountered an error: {str(e)}"
            slack_integration.send_slack_message(os.environ.get("SLACK_CHANNEL_ID"), error_message)
        except Exception as inner_e:
            logger.error(f"Failed to send error notification: {str(inner_e)}")
        raise



if __name__ == "__main__":
    from dotenv import load_dotenv
    # This block is only for local testing, not needed in Azure Functions
    load_dotenv()  # Load environment variables from .env file
    logging.basicConfig(level=logging.INFO)
    class DummyTimer:
        past_due = False
    expirationDateNotice(DummyTimer())
    logging.warning('Local test executed successfully.')