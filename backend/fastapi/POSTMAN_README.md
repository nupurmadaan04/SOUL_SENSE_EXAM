# SoulSense API Postman Collection

This directory contains a pre-configured Postman Collection to help you test and develop against the SoulSense API (v1).

## Getting Started

1.  **Import**:
    - Open Postman.
    - Click "Import" -> "File" -> Select `SoulSense_API_v1.postman_collection.json`.

2.  **Environment Setup**:
    - The collection uses a variable `{{base_url}}` which defaults to `http://localhost:8000/api/v1`.
    - You do NOT need to manually set the `access_token`.

3.  **Authentication Flow**:
    - Go to the **Auth** folder.
    - Run the **Register** request (it uses a timestamp to create a unique user each time).
    - Run the **Login** request.
    - **Magic**: The Login request has a "Test Script" that automatically captures the token and saves it to your Postman environment as `access_token`.
    - All other requests (Journal, Users, etc.) will now automatically use this token.

## Included Folders

- **Auth**: Registration and Login.
- **Journal**: Create, List, and Analyze journal entries.
- **Settings Sync**: Test the new synchronization API.
- **Profiles**: View user profile data.
- **Health**: Check API status.

## Contributing

If you add new endpoints to the API, please export the updated collection and update `SoulSense_API_v1.postman_collection.json` in your PR.
