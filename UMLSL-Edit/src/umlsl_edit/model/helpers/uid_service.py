def generate_uid() -> str:
    """Generate a unique identifier."""
    import uuid

    return str(uuid.uuid4())