"""Tests for M6 Item 3 — PWA client structure validation.

These tests verify the PWA client scaffolding exists and is properly structured.
They do NOT require Node.js or npm install to run.
"""
import json
import os

import pytest

CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")


def test_client_directory_exists():
    assert os.path.isdir(CLIENT_DIR), "client/ directory must exist"


def test_package_json_exists_and_valid():
    pkg_path = os.path.join(CLIENT_DIR, "package.json")
    assert os.path.isfile(pkg_path)
    with open(pkg_path) as f:
        pkg = json.load(f)
    assert pkg["name"] == "travel-agent-pwa"
    assert "next" in pkg["dependencies"]
    assert "react" in pkg["dependencies"]
    assert "tailwindcss" in pkg["devDependencies"]


def test_manifest_json_valid():
    manifest_path = os.path.join(CLIENT_DIR, "public", "manifest.json")
    assert os.path.isfile(manifest_path)
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert manifest["name"] == "Travel Agent"
    assert manifest["display"] == "standalone"
    assert len(manifest["icons"]) >= 2


def test_next_config_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "next.config.js"))


def test_tsconfig_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "tsconfig.json"))


def test_tailwind_config_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "tailwind.config.ts"))


def test_app_layout_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "src", "app", "layout.tsx"))


def test_app_page_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "src", "app", "page.tsx"))


def test_app_providers_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "src", "app", "providers.tsx"))


def test_components_exist():
    components_dir = os.path.join(CLIENT_DIR, "src", "components")
    expected = [
        "TripForm.tsx",
        "TripTimeline.tsx",
        "TripList.tsx",
        "VoiceInputButton.tsx",
        "Toast.tsx",
        "AuthGate.tsx",
    ]
    for name in expected:
        assert os.path.isfile(os.path.join(components_dir, name)), f"Missing component: {name}"


def test_hooks_exist():
    hooks_dir = os.path.join(CLIENT_DIR, "src", "hooks")
    expected = ["useWebSocket.ts", "usePushNotifications.ts"]
    for name in expected:
        assert os.path.isfile(os.path.join(hooks_dir, name)), f"Missing hook: {name}"


def test_api_client_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "src", "lib", "api.ts"))


def test_service_worker_exists():
    assert os.path.isfile(os.path.join(CLIENT_DIR, "public", "sw.js"))


def test_pwa_icons_exist():
    public_dir = os.path.join(CLIENT_DIR, "public")
    assert os.path.isfile(os.path.join(public_dir, "icon-192x192.png"))
    assert os.path.isfile(os.path.join(public_dir, "icon-512x512.png"))


def test_voice_input_component_has_speech_recognition():
    """VoiceInputButton references Web Speech API."""
    voice_path = os.path.join(CLIENT_DIR, "src", "components", "VoiceInputButton.tsx")
    with open(voice_path) as f:
        content = f.read()
    assert "SpeechRecognition" in content
    assert "onResult" in content


def test_push_hook_has_push_manager():
    """usePushNotifications references PushManager."""
    push_path = os.path.join(CLIENT_DIR, "src", "hooks", "usePushNotifications.ts")
    with open(push_path) as f:
        content = f.read()
    assert "PushManager" in content
    assert "subscribe" in content


# ── New: Auth, Toast, and API client content tests ─────────────────────────


def test_auth_gate_has_login_form():
    """AuthGate includes a LoginForm and AuthProvider."""
    auth_path = os.path.join(CLIENT_DIR, "src", "components", "AuthGate.tsx")
    with open(auth_path) as f:
        content = f.read()
    assert "LoginForm" in content
    assert "AuthProvider" in content
    assert "localStorage" in content


def test_toast_has_provider_and_hook():
    """Toast component includes ToastProvider and useToast."""
    toast_path = os.path.join(CLIENT_DIR, "src", "components", "Toast.tsx")
    with open(toast_path) as f:
        content = f.read()
    assert "ToastProvider" in content
    assert "useToast" in content
    assert "error" in content
    assert "success" in content


def test_api_client_has_create_trip_options():
    """API client supports extended trip creation fields."""
    api_path = os.path.join(CLIENT_DIR, "src", "lib", "api.ts")
    with open(api_path) as f:
        content = f.read()
    assert "CreateTripOptions" in content
    assert "total_budget" in content
    assert "org_id" in content
    assert "policy_id" in content
    assert "clearToken" in content
    assert "checkAuth" in content


def test_trip_form_has_travel_fields():
    """TripForm includes destination, duration, airline, stay, and budget fields."""
    form_path = os.path.join(CLIENT_DIR, "src", "components", "TripForm.tsx")
    with open(form_path) as f:
        content = f.read()
    assert "destination" in content
    assert "duration" in content
    assert "airline" in content
    assert "stayType" in content
    assert "total_budget" in content


def test_websocket_hook_has_reconnection():
    """useWebSocket includes retry/reconnection logic."""
    ws_path = os.path.join(CLIENT_DIR, "src", "hooks", "useWebSocket.ts")
    with open(ws_path) as f:
        content = f.read()
    assert "MAX_RETRIES" in content
    assert "retriesRef" in content
    assert "retryTimerRef" in content


def test_page_uses_toast_and_auth():
    """Main page uses useToast and useAuth."""
    page_path = os.path.join(CLIENT_DIR, "src", "app", "page.tsx")
    with open(page_path) as f:
        content = f.read()
    assert "useToast" in content
    assert "useAuth" in content
    assert "usePushNotifications" in content
    assert "toast(" in content


def test_env_example_exists():
    """A .env.example file exists at the repo root."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    assert os.path.isfile(env_path), ".env.example must exist at repo root"
    with open(env_path) as f:
        content = f.read()
    assert "ANTHROPIC_API_KEY" in content
    assert "AUTH_SECRET" in content
    assert "VAPID_PUBLIC_KEY" in content
