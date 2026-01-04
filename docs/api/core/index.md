# Core Module

The `sok.core` module contains the fundamental interfaces, managers, and utilities
that form the backbone of S.O.K.

## Overview

```mermaid
classDiagram
    class MediaAPI {
        <<abstract>>
        +supported_media_types: List[MediaType]
        +supported_content_types: List[ContentType]
        +search(query, content_type) Dict
        +get_details(item_id, content_type) Dict
        +get_related_items(item_id, content_type) List
    }

    class MediaItem {
        <<abstract>>
        +title: str
        +media_type: MediaType
        +content_type: ContentType
        +get_formatted_name() str
        +get_folder_structure() List[str]
    }

    class UniversalMediaManager {
        +apis: Dict[str, MediaAPI]
        +search(query, media_type) Dict
        +get_details(item_id, media_type) Dict
        +register_api(name, api)
    }

    UniversalMediaManager --> MediaAPI
```

## Submodules

- [Interfaces](interfaces.md) - Abstract base classes
- [Media Manager](media_manager.md) - Central orchestrator
- [Exceptions](exceptions.md) - Error handling
- [Utils](utils.md) - Utility functions
