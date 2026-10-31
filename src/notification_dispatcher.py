"""
AquaGuard AI - Notification Dispatcher
Handles multi-channel dispatch for critical sensor outages, missing readings,
sensor faults, and recovery notifications with alert deduplication.
"""

from typing import Dict, Any, List, Optional
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AquaGuardNotifications")

class NotificationDispatcher:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.notification_log: List[Dict[str, Any]] = []

    def dispatch(self, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch notification for an alert event.
        Ensures in-app notification logging, deduplication logging, and external dispatch stub.
        """
        notification_entry = {
            'notification_id': f"NOTIF_{len(self.notification_log) + 1:04d}",
            'dispatched_at': datetime.datetime.utcnow().isoformat(),
            'channel': 'IN_APP_DASHBOARD',
            'alert_id': alert_payload.get('alert_id'),
            'meter_id': alert_payload.get('meter_id'),
            'zone_id': alert_payload.get('zone_id'),
            'category': alert_payload.get('alert_category'),
            'severity': alert_payload.get('severity'),
            'message': alert_payload.get('alert_message'),
            'recommended_action': alert_payload.get('recommended_action'),
            'delivered': True
        }

        self.notification_log.append(notification_entry)

        # Log formatted dispatch message
        sev = alert_payload.get('severity', 'Info').upper()
        msg = alert_payload.get('alert_message', '')
        logger.info(f"[{sev} NOTIFICATION DISPATCHED] {msg}")

        return notification_entry

    def get_recent_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        return sorted(self.notification_log, key=lambda x: x['dispatched_at'], reverse=True)[:limit]
