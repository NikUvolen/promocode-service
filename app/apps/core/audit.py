from core.models import AuditLog


def log_audit_event(
    event_type,
    *,
    actor=None,
    target=None,
    metadata=None,
):
    target_model = ''
    target_object_id = ''
    if target is not None and getattr(target, '_meta', None) is not None:
        target_model = target._meta.label
        target_object_id = str(target.pk)

    return AuditLog.objects.create(
        event_type=event_type,
        actor=actor if getattr(actor, 'pk', None) else None,
        target_model=target_model,
        target_object_id=target_object_id,
        metadata=metadata or {},
    )
