# UI Components Reference

This document provides a reference guide for all major UI components in the `app/ui/components/` directory.

## AvatarCropper

**File:** `app/ui/components/image_cropper.py`

A modal dialog window for cropping and adjusting profile pictures. Provides an interactive interface with drag-to-move and scroll-to-zoom functionality, displaying a circular crop area.

### Public Methods

- `__init__(parent, image_path, output_path, on_complete)`: Initialize the cropper dialog
  - `parent`: Parent Tkinter window
  - `image_path`: Path to the input image file
  - `output_path`: Path where the cropped image will be saved
  - `on_complete`: Callback function called when cropping is complete

- `save_crop()`: Save the cropped image and close the dialog

### Usage Example

```python
from app.ui.components.image_cropper import AvatarCropper

def on_crop_complete():
    print("Profile picture updated!")

cropper = AvatarCropper(
    parent=root_window,
    image_path="user_photo.jpg",
    output_path="avatar.png",
    on_complete=on_crop_complete
)
```

## LoadingOverlay

**File:** `app/ui/components/loading_overlay.py`

A modal loading overlay that displays an animated spinner and customizable message. Covers the parent window to prevent user interaction during long-running operations.

### Public Methods

- `__init__(parent, message="Loading...", bg_color="#0F172A", fg_color="#F8FAFC", accent_color="#3B82F6")`: Create a loading overlay
  - `parent`: Parent window to overlay
  - `message`: Loading message to display
  - `bg_color`: Background color of the overlay
  - `fg_color`: Text color
  - `accent_color`: Spinner color

- `update_message(message)`: Update the loading message
  - `message`: New message to display

- `destroy()`: Clean up and destroy the overlay

### Utility Functions

- `show_loading(parent, message="Loading...")`: Show a loading overlay
  - Returns: LoadingOverlay instance

- `hide_loading(overlay)`: Safely hide and destroy a loading overlay
  - `overlay`: LoadingOverlay instance to destroy

### Usage Example

```python
from app.ui.components.loading_overlay import show_loading, hide_loading

# Show loading overlay
overlay = show_loading(parent_window, "Processing data...")

# Perform long operation
process_data()

# Update message if needed
overlay.update_message("Almost done...")

# Hide overlay
hide_loading(overlay)
```

## TagInput

**File:** `app/ui/components/tag_input.py`

A component for adding and removing text tags (chips). Features input validation, deduplication, and optional suggestions.

### Public Methods

- `__init__(parent, tags=None, on_change=None, max_tags=10, max_char=25, colors=None, suggestion_list=None)`: Initialize the tag input component
  - `parent`: Parent widget
  - `tags`: Initial list of tag strings
  - `on_change`: Callback function called when tags change (receives tags list)
  - `max_tags`: Maximum number of tags allowed (default 10)
  - `max_char`: Maximum characters per tag (default 25)
  - `colors`: Dictionary of app colors
  - `suggestion_list`: Optional list of suggested tags

- `get_tags()`: Get the current list of tags
  - Returns: List of tag strings

### Usage Example

```python
from app.ui.components.tag_input import TagInput

def on_tags_changed(tags):
    print(f"Tags updated: {tags}")

tag_input = TagInput(
    parent=container,
    tags=["Python", "AI"],
    on_change=on_tags_changed,
    max_tags=5,
    suggestion_list=["JavaScript", "React", "Django"]
)

# Get current tags
current_tags = tag_input.get_tags()
```

## LifeTimeline

**File:** `app/ui/components/timeline.py`

An interactive timeline component for displaying life events. Shows events in chronological order with visual timeline layout.

### Public Methods

- `__init__(parent, events=None, on_add=None, colors=None)`: Initialize the timeline component
  - `parent`: Parent widget
  - `events`: List of event dictionaries with keys: 'date', 'title', 'description', 'impact'
  - `on_add`: Callback function called when "Add Event" is clicked
  - `colors`: Dictionary of app colors

- `refresh(events)`: Update the timeline with new events
  - `events`: New list of event dictionaries

### Usage Example

```python
from app.ui.components.timeline import LifeTimeline

events = [
    {
        "date": "2023-01-15",
        "title": "Started New Job",
        "description": "Joined Tech Corp as Senior Developer",
        "impact": "positive"
    },
    {
        "date": "2022-06-01",
        "title": "Graduated University",
        "description": "Completed Bachelor's in Computer Science",
        "impact": "milestone"
    }
]

def on_add_event():
    # Open add event dialog
    pass

timeline = LifeTimeline(
    parent=container,
    events=events,
    on_add=on_add_event
)

# Update events later
new_events = events + [new_event]
timeline.refresh(new_events)
```</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\docs\api\ui_components.md