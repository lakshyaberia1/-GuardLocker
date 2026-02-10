"""
GuardLocker - Honey Account Monitoring System
Detects vault breaches through login attempts on honey accounts
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitoringService(Enum):
    """Supported monitoring services"""
    EMAIL = "email"
    GMAIL_API = "gmail_api"
    GITHUB_API = "github_api"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


@dataclass
class BreachAlert:
    """Alert when honey account is accessed"""
    honey_account_id: str
    website: str
    username: str
    timestamp: datetime
    ip_address: Optional[str] = None
    location: Optional[str] = None
    device_info: Optional[str] = None
    severity: str = "HIGH"
    
    def to_dict(self) -> dict:
        return {
            'honey_account_id': self.honey_account_id,
            'website': self.website,
            'username': self.username,
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'location': self.location,
            'device_info': self.device_info,
            'severity': self.severity
        }


@dataclass
class MonitorConfig:
    """Configuration for monitoring"""
    check_interval_seconds: int = 300  # 5 minutes
    email_alerts_enabled: bool = True
    webhook_url: Optional[str] = None
    max_retries: int = 3
    alert_cooldown_minutes: int = 60
    
    # Email configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    alert_recipients: List[str] = field(default_factory=list)


class HoneyAccountMonitor:
    """
    Monitors honey accounts for unauthorized access
    
    Features:
    - Multiple monitoring services (email, APIs, webhooks)
    - Configurable check intervals
    - Alert notifications
    - Rate limiting and cooldowns
    """
    
    def __init__(self, config: MonitorConfig):
        """
        Initialize monitor
        
        Args:
            config: Monitoring configuration
        """
        self.config = config
        self.monitoring_tasks = []
        self.last_alerts = {}  # Track last alert time per account
        self.running = False
    
    async def start_monitoring(
        self,
        honey_accounts: List[Dict],
        alert_callback: Optional[Callable] = None
    ):
        """
        Start monitoring honey accounts
        
        Args:
            honey_accounts: List of honey account configurations
            alert_callback: Optional callback function for alerts
        """
        self.running = True
        logger.info(f"Starting monitoring for {len(honey_accounts)} honey accounts")
        
        # Create monitoring task for each account
        for account in honey_accounts:
            task = asyncio.create_task(
                self._monitor_account(account, alert_callback)
            )
            self.monitoring_tasks.append(task)
        
        # Wait for all tasks
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
    
    async def stop_monitoring(self):
        """Stop all monitoring tasks"""
        self.running = False
        logger.info("Stopping honey account monitoring")
        
        for task in self.monitoring_tasks:
            task.cancel()
        
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        self.monitoring_tasks = []
    
    async def _monitor_account(
        self,
        account: Dict,
        alert_callback: Optional[Callable] = None
    ):
        """
        Monitor a single honey account
        
        Args:
            account: Honey account configuration
            alert_callback: Optional callback for alerts
        """
        account_id = account.get('id', account['username'])
        service = MonitoringService(account.get('monitoring_service', 'email'))
        
        while self.running:
            try:
                # Check for login attempts
                login_detected = await self._check_login_attempt(account, service)
                
                if login_detected:
                    # Check cooldown
                    if self._should_send_alert(account_id):
                        alert = BreachAlert(
                            honey_account_id=account_id,
                            website=account['website'],
                            username=account['username'],
                            timestamp=datetime.now(),
                            ip_address=login_detected.get('ip_address'),
                            location=login_detected.get('location'),
                            device_info=login_detected.get('device')
                        )
                        
                        # Send alert
                        await self._send_alert(alert)
                        
                        # Update last alert time
                        self.last_alerts[account_id] = datetime.now()
                        
                        # Call callback if provided
                        if alert_callback:
                            await alert_callback(alert)
                
                # Wait before next check
                await asyncio.sleep(self.config.check_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for {account_id}")
                break
            except Exception as e:
                logger.error(f"Error monitoring {account_id}: {e}")
                await asyncio.sleep(self.config.check_interval_seconds)
    
    async def _check_login_attempt(
        self,
        account: Dict,
        service: MonitoringService
    ) -> Optional[Dict]:
        """
        Check if login attempt detected
        
        Args:
            account: Honey account configuration
            service: Monitoring service to use
        
        Returns:
            Login details if detected, None otherwise
        """
        if service == MonitoringService.EMAIL:
            return await self._check_email_notifications(account)
        elif service == MonitoringService.GMAIL_API:
            return await self._check_gmail_api(account)
        elif service == MonitoringService.GITHUB_API:
            return await self._check_github_api(account)
        elif service == MonitoringService.WEBHOOK:
            return await self._check_webhook(account)
        else:
            return await self._check_custom(account)
    
    async def _check_email_notifications(self, account: Dict) -> Optional[Dict]:
        """
        Check for login notification emails
        
        This is a simplified example. Real implementation would use
        IMAP to check for specific emails.
        """
        # TODO: Implement IMAP email checking
        # Look for emails from the website with login notifications
        # Parse email content for IP, location, device info
        
        logger.debug(f"Checking email for {account['website']}")
        return None
    
    async def _check_gmail_api(self, account: Dict) -> Optional[Dict]:
        """Check Gmail API for login notifications"""
        # TODO: Implement Gmail API checking
        logger.debug(f"Checking Gmail API for {account['website']}")
        return None
    
    async def _check_github_api(self, account: Dict) -> Optional[Dict]:
        """
        Check GitHub API for login activity
        
        GitHub provides security events API
        """
        if account['website'] != 'github.com':
            return None
        
        # TODO: Implement GitHub API checking
        # Use Personal Access Token to check security events
        # GET /user/events (filter for security events)
        
        logger.debug("Checking GitHub API for login activity")
        return None
    
    async def _check_webhook(self, account: Dict) -> Optional[Dict]:
        """Check webhook endpoint for login notifications"""
        webhook_url = account.get('webhook_url')
        if not webhook_url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(webhook_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('login_detected'):
                            return data.get('login_details')
        except Exception as e:
            logger.error(f"Webhook check failed: {e}")
        
        return None
    
    async def _check_custom(self, account: Dict) -> Optional[Dict]:
        """Custom checking logic"""
        # Implement custom checking logic here
        return None
    
    def _should_send_alert(self, account_id: str) -> bool:
        """Check if alert should be sent (cooldown check)"""
        if account_id not in self.last_alerts:
            return True
        
        last_alert = self.last_alerts[account_id]
        cooldown = timedelta(minutes=self.config.alert_cooldown_minutes)
        
        return datetime.now() - last_alert > cooldown
    
    async def _send_alert(self, alert: BreachAlert):
        """
        Send breach alert via configured channels
        
        Args:
            alert: Breach alert to send
        """
        logger.warning(f"BREACH DETECTED: {alert.to_dict()}")
        
        # Send email alert
        if self.config.email_alerts_enabled:
            await self._send_email_alert(alert)
        
        # Send webhook alert
        if self.config.webhook_url:
            await self._send_webhook_alert(alert)
    
    async def _send_email_alert(self, alert: BreachAlert):
        """Send email alert"""
        if not self.config.alert_recipients:
            logger.warning("No email recipients configured")
            return
        
        try:
            subject = f"🚨 VAULT BREACH DETECTED - {alert.website}"
            
            body = f"""
GUARDLOCKER SECURITY ALERT

A honey account has been accessed, indicating a possible vault breach.

Details:
- Website: {alert.website}
- Username: {alert.username}
- Timestamp: {alert.timestamp.isoformat()}
- IP Address: {alert.ip_address or 'Unknown'}
- Location: {alert.location or 'Unknown'}
- Device: {alert.device_info or 'Unknown'}

RECOMMENDED ACTIONS:
1. Change your master password immediately
2. Review all account passwords
3. Enable two-factor authentication on critical accounts
4. Check for unauthorized access on your accounts

If this was not you, your password vault may have been compromised.

---
GuardLocker Security Team
            """
            
            # Send email
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_username
            msg['To'] = ', '.join(self.config.alert_recipients)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Use asyncio to run blocking SMTP in executor
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_smtp_email,
                msg
            )
            
            logger.info(f"Email alert sent to {len(self.config.alert_recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_smtp_email(self, msg: MIMEMultipart):
        """Send SMTP email (blocking)"""
        with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
            server.starttls()
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.send_message(msg)
    
    async def _send_webhook_alert(self, alert: BreachAlert):
        """Send webhook alert"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=alert.to_dict()
                ) as response:
                    if response.status == 200:
                        logger.info("Webhook alert sent successfully")
                    else:
                        logger.error(f"Webhook alert failed: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")


class HoneyAccountGenerator:
    """Generate honey accounts for breach detection"""
    
    # Websites that provide login notifications
    MONITORED_WEBSITES = [
        {
            'domain': 'github.com',
            'supports_api': True,
            'supports_email': True,
            'monitoring_service': MonitoringService.GITHUB_API
        },
        {
            'domain': 'gmail.com',
            'supports_api': True,
            'supports_email': True,
            'monitoring_service': MonitoringService.GMAIL_API
        },
        {
            'domain': 'dropbox.com',
            'supports_api': False,
            'supports_email': True,
            'monitoring_service': MonitoringService.EMAIL
        },
        # Add more websites
    ]
    
    def __init__(self, vault_model):
        """
        Initialize generator
        
        Args:
            vault_model: Trained vault model for password generation
        """
        self.vault_model = vault_model
    
    def generate_honey_accounts(
        self,
        count: int = 10,
        use_random_usernames: bool = True
    ) -> List[Dict]:
        """
        Generate honey accounts
        
        Args:
            count: Number of honey accounts to generate
            use_random_usernames: Whether to use random usernames
        
        Returns:
            List of honey account configurations
        """
        import secrets
        import string
        
        honey_accounts = []
        
        for i in range(count):
            # Select website
            website = secrets.choice(self.MONITORED_WEBSITES)
            
            # Generate username
            if use_random_usernames:
                username = self._generate_random_username()
            else:
                username = f"honeyaccount{i+1}"
            
            # Generate password from model
            password = self.vault_model.generate_password(
                '<SEP>',
                self.vault_model.tokenizer,
                temperature=0.9
            )
            
            honey_accounts.append({
                'id': f'honey_{secrets.token_hex(8)}',
                'website': website['domain'],
                'username': username,
                'password': password,
                'monitoring_service': website['monitoring_service'].value,
                'created_at': datetime.now().isoformat(),
                'is_honey': True
            })
        
        return honey_accounts
    
    def _generate_random_username(self) -> str:
        """Generate random username"""
        import secrets
        import string
        
        # Random alphanumeric username (8-12 chars)
        length = secrets.randbelow(5) + 8
        alphabet = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))


# Example usage
if __name__ == "__main__":
    async def main():
        # Configure monitoring
        config = MonitorConfig(
            check_interval_seconds=60,  # Check every minute
            email_alerts_enabled=True,
            smtp_username="your-email@gmail.com",
            smtp_password="your-app-password",
            alert_recipients=["user@example.com"],
            alert_cooldown_minutes=30
        )
        
        # Create sample honey accounts
        honey_accounts = [
            {
                'id': 'honey_1',
                'website': 'github.com',
                'username': 'decoyuser123',
                'password': 'HoneyPassword1!',
                'monitoring_service': 'github_api'
            },
            {
                'id': 'honey_2',
                'website': 'gmail.com',
                'username': 'decoy@gmail.com',
                'password': 'HoneyPassword2!',
                'monitoring_service': 'gmail_api'
            }
        ]
        
        # Custom alert callback
        async def on_breach_detected(alert: BreachAlert):
            print(f"\n🚨 BREACH ALERT: {alert.website}")
            print(f"Account: {alert.username}")
            print(f"Time: {alert.timestamp}")
            print("\nTake immediate action to secure your vault!")
        
        # Initialize and start monitor
        monitor = HoneyAccountMonitor(config)
        
        print("Starting honey account monitoring...")
        print(f"Monitoring {len(honey_accounts)} accounts")
        print("Press Ctrl+C to stop\n")
        
        try:
            await monitor.start_monitoring(honey_accounts, on_breach_detected)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
            await monitor.stop_monitoring()
    
    # Run monitoring
    asyncio.run(main())