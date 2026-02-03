from typing import List, Set

class ReviewConfig:
    """Central configuration for risk paths and exclusions."""

    # Paths that should trigger extra scrutiny in reviews
    RISK_PATHS = {
        'auth/', 'security/', 'payment/', 'crypto/', 'secrets/', 
        'migrations/', 'schemas/', 'models/', 'infrastructure/',
        '.github/workflows/', 'Dockerfile', 'docker-compose'
    }

    # Files that should NEVER be included in a review packet
    CORE_EXCLUSIONS = {
        '.env', '.env.local', '.env.development', '.env.test', '.env.production',
        '*.pem', '*.key', 'credentials', 'secrets.json'
    }

    @classmethod
    def is_risk_path(cls, file_path: str) -> bool:
        """Check if a file path is considered high-risk."""
        return any(file_path.startswith(risk) or risk in file_path for risk in cls.RISK_PATHS)

    @classmethod
    def should_exclude(cls, file_path: str) -> bool:
        """Check if a file should be excluded regardless of git status."""
        filename = file_path.split('/')[-1]
        if filename in cls._exclusions_exact():
            return True
        if any(filename.endswith(ext.replace('*', '')) for ext in cls.CORE_EXCLUSIONS if '*' in ext):
            return True
        return False

    @classmethod
    def _exclusions_exact(cls) -> Set[str]:
        return {e for e in cls.CORE_EXCLUSIONS if '*' not in e}
