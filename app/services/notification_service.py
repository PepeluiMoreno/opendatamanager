"""
Notification Service - Sends webhooks to subscribed applications.
"""
import hmac
import hashlib
from typing import Optional
import json
import requests
from typing import List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Dataset, ResourceSubscription, Subscriber, SubscriberNotification
from app.utils.versioning import compute_schema_diff


class NotificationService:
    """Service for sending webhook notifications to applications"""

    def notify_subscribers(self, session: Session, dataset: Dataset):
        """
        Send notifications to all subscribed applications.

        Args:
            session: SQLAlchemy session
            dataset: Newly created Dataset
        """
        print(f"  [5/5] NOTIFY - Sending notifications for dataset {dataset.version_string}...")

        # Get matching subscriptions for this resource
        subscriptions = (
            session.query(ResourceSubscription)
            .join(Subscriber)
            .filter(ResourceSubscription.resource_id == dataset.resource_id)
            .filter(Subscriber.active == True)
            .all()
        )

        if not subscriptions:
            print(f"    No active subscriptions")
            return

        for subscription in subscriptions:
            app = subscription.application
            mode = app.consumption_mode or "webhook"

            if mode in ("webhook", "both") and not app.webhook_url:
                print(f"    Subscriber '{app.name}' has no webhook_url — skipping")
                continue

            if mode == "graphql":
                # Notificación ligera: avisa que hay datos nuevos sin incluir URLs de descarga masiva
                payload = self._build_graphql_payload(session, dataset, subscription)
            else:
                # webhook / both: payload completo con URLs de descarga JSONL
                payload = self._build_payload(session, dataset, subscription)

            # Version pinning: si la suscripción fija una versión y la nueva no la
            # satisface, no se notifica (el consumidor eligió quedarse anclado).
            if subscription.pinned_version and not self._version_satisfies_pin(
                dataset.version_string, subscription.pinned_version
            ):
                print(f"    Skipping '{app.name}': {dataset.version_string} no satisface pin {subscription.pinned_version}")
                continue

            # Política auto_upgrade. Un cambio MAJOR (rotura) siempre se notifica,
            # aunque la política no lo auto-acepte: el consumidor debe enterarse y
            # actuar. En ese caso se marca como bloqueado para auto-upgrade.
            new_version_type = payload["dataset"]["version_type"]
            auto_ok = self._should_notify(subscription.auto_upgrade, new_version_type)
            if not auto_ok and new_version_type != "major":
                print(f"    Skipping notification for '{app.name}' due to auto_upgrade policy ({subscription.auto_upgrade} vs {new_version_type})")
                continue
            payload["auto_upgrade"] = {
                "policy": subscription.auto_upgrade,
                "applies": auto_ok,
                "requires_action": (not auto_ok) and new_version_type == "major",
            }

            # Sign with HMAC
            signature = self._compute_hmac(payload, app.webhook_secret or "")

            # Send webhook
            try:
                response = requests.post(
                    app.webhook_url,
                    json=payload,
                    headers={
                        "X-ODM-Signature": signature,
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )

                # Log notification
                notification = SubscriberNotification(
                    application_id=app.id,
                    dataset_id=dataset.id,
                    sent_at=datetime.utcnow(),
                    status_code=response.status_code,
                    response_body=response.text[:1000]
                )
                session.add(notification)

                print(f"    Notified '{app.name}' - Status {response.status_code}")

            except Exception as e:
                # Log error
                notification = SubscriberNotification(
                    application_id=app.id,
                    dataset_id=dataset.id,
                    sent_at=datetime.utcnow(),
                    error_message=str(e)
                )
                session.add(notification)

                print(f"    Error notifying '{app.name}': {e}")

        session.commit()

    def _should_notify(self, auto_upgrade_policy: Optional[str], new_version_type: str) -> bool:
        """
        Determines if a notification should be sent based on the auto_upgrade policy.
        """
        if not auto_upgrade_policy or auto_upgrade_policy == "major":
            return True  # Always notify if policy is major or not set
        
        if auto_upgrade_policy == "minor":
            return new_version_type in ["patch", "minor"]
        
        if auto_upgrade_policy == "patch":
            return new_version_type == "patch"
            
        return False # Default to not notifying

    def _build_graphql_payload(self, session: Session, dataset: Dataset, subscription: ResourceSubscription = None) -> Dict:
        """
        Payload ligero para aplicaciones que consumen datos vía GraphQL.

        No incluye URLs de descarga masiva: la app consulta /graphql/data
        directamente con los filtros que necesite.
        """
        from app.graphql_data.schema_builder import dataset_query_name
        from app.models import Resource as ResourceModel
        resource = session.get(ResourceModel, dataset.resource_id)
        return {
            "event": "dataset.published",
            "consumption_mode": "graphql",
            "dataset": {
                "id": str(dataset.id),
                "resource_id": str(resource.id),
                "resource_name": resource.name,
                "version": dataset.version_string,
                "version_type": self._version_type(
                    self._schema_diff_for_subscription(session, dataset, resource, subscription)
                ),
                "created_at": dataset.created_at.isoformat(),
                "record_count": dataset.record_count,
            },
            "graphql": {
                "endpoint": "/graphql/data",
                "query_name": dataset_query_name(resource.name),
                "hint": f'{{ {dataset_query_name(resource.name)}(limit: 100) {{ total items {{ ... }} }} }}',
            },
        }

    def _schema_diff_for_subscription(self, session, dataset, resource, subscription) -> Dict:
        """Diff de esquema respecto a la versión que el suscriptor tiene actualmente.

        Si no hay suscripción o versión previa conocida, devuelve {} (→ patch).
        """
        if not subscription or not getattr(subscription, "current_version", None):
            return {}
        prev_parts = subscription.current_version.split('.')
        if len(prev_parts) != 3:
            return {}
        prev_dataset = (
            session.query(Dataset)
            .filter(Dataset.resource_id == resource.id)
            .filter(Dataset.major_version == int(prev_parts[0]))
            .filter(Dataset.minor_version == int(prev_parts[1]))
            .filter(Dataset.patch_version == int(prev_parts[2]))
            .first()
        )
        if not prev_dataset:
            return {}
        return compute_schema_diff(prev_dataset.schema_json, dataset.schema_json)

    @staticmethod
    def _version_satisfies_pin(version_string: str, pin: str) -> bool:
        """Delegado a app.utils.versioning.version_satisfies_pin (función pura)."""
        from app.utils.versioning import version_satisfies_pin
        return version_satisfies_pin(version_string, pin)

    def _build_payload(
        self,
        session: Session,
        dataset: Dataset,
        subscription: ResourceSubscription
    ) -> Dict:
        """Build notification payload"""
        from app.models import Resource as ResourceModel
        resource = session.get(ResourceModel, dataset.resource_id)

        # Compute schema diff if there's a previous version
        schema_diff = {}
        if subscription.current_version:
            # Find previous dataset
            prev_parts = subscription.current_version.split('.')
            if len(prev_parts) == 3:
                prev_dataset = (
                    session.query(Dataset)
                    .filter(Dataset.resource_id == resource.id)
                    .filter(Dataset.major_version == int(prev_parts[0]))
                    .filter(Dataset.minor_version == int(prev_parts[1]))
                    .filter(Dataset.patch_version == int(prev_parts[2]))
                    .first()
                )
                if prev_dataset:
                    schema_diff = compute_schema_diff(
                        prev_dataset.schema_json,
                        dataset.schema_json
                    )

        return {
            "event": "dataset.published",
            "dataset": {
                "id": str(dataset.id),
                "resource_id": str(resource.id),
                "resource_name": resource.name,
                "publisher": resource.publisher,
                "version": dataset.version_string,
                "version_type": self._version_type(schema_diff),
                "created_at": dataset.created_at.isoformat(),
                "record_count": dataset.record_count,
                "checksum": dataset.checksum
            },
            "schema_diff": schema_diff,
            "download_urls": {
                "data": f"/api/datasets/{dataset.id}/data.jsonl",
                "schema": f"/api/datasets/{dataset.id}/schema.json",
                "models": f"/api/datasets/{dataset.id}/models.py",
                "metadata": f"/api/datasets/{dataset.id}/metadata.json"
            }
        }

    def _version_type(self, schema_diff: Dict) -> str:
        """Determina el tipo de versión a partir del diff de esquema."""
        if not schema_diff:
            return "patch"
        if schema_diff.get("breaking_changes"):
            return "major"
        elif schema_diff.get("minor_changes") or schema_diff.get("added_fields"):
            return "minor"
        else:
            return "patch"

    def _compute_hmac(self, payload: Dict, secret: str) -> str:
        """Compute HMAC-SHA256 signature"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        secret_bytes = secret.encode('utf-8')
        return hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
