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


def test_components_exist():
    components_dir = os.path.join(CLIENT_DIR, "src", "components")
    expected = ["TripForm.tsx", "TripTimeline.tsx", "TripList.tsx", "VoiceInputButton.tsx"]
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
