# Configuration Module

The `sok.config` module handles all configuration, settings, and session management.

## Overview

Configuration is split into three main components:

- **Config Manager**: Application settings and preferences
- **Session Manager**: API keys, OAuth tokens, and credentials
- **API Registry**: Service discovery and configuration

```mermaid
classDiagram
    class ConfigManager {
        +config_path: Path
        +get(key, default) Any
        +set(key, value)
        +save()
        +load()
    }

    class SessionManager {
        +get_api_key(service) str
        +set_api_key(service, key)
        +get_oauth_token(service) str
    }

    class APIRegistry {
        +register_service(name, config)
        +get_services_by_media_type(type) List
    }
```

## Submodules

- [Config Manager](config_manager.md) - Application settings
- [Session Manager](session_manager.md) - API keys and tokens
- [API Registry](api_registry.md) - Service discovery
