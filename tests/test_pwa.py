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
        "TripDetail.tsx",
        "Settings.tsx",
        "BottomNav.tsx",
        "InstallPrompt.tsx",
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


def test_trip_detail_has_booking_breakdown():
    """TripDetail shows cost breakdown by domain and booking details."""
    detail_path = os.path.join(CLIENT_DIR, "src", "components", "TripDetail.tsx")
    with open(detail_path) as f:
        content = f.read()
    assert "costByDomain" in content
    assert "BookingData" in content
    assert "onCancel" in content
    assert "summary_text" in content


def test_settings_has_preferences():
    """Settings component stores org and travel preferences."""
    settings_path = os.path.join(CLIENT_DIR, "src", "components", "Settings.tsx")
    with open(settings_path) as f:
        content = f.read()
    assert "orgId" in content
    assert "cabinClass" in content
    assert "localStorage" in content
    assert "getSavedPreferences" in content


def test_timeline_has_smart_defaults():
    """TripTimeline handles smart_defaults event type."""
    tl_path = os.path.join(CLIENT_DIR, "src", "components", "TripTimeline.tsx")
    with open(tl_path) as f:
        content = f.read()
    assert "smart_defaults" in content
    assert "SmartDefaultsCard" in content
    assert "BudgetTierCard" in content
    assert "ApprovalCard" in content


def test_trip_list_has_search_and_filter():
    """TripList includes search input and status filter."""
    list_path = os.path.join(CLIENT_DIR, "src", "components", "TripList.tsx")
    with open(list_path) as f:
        content = f.read()
    assert "search" in content
    assert "statusFilter" in content
    assert "filtered" in content


def test_api_client_has_cancel_trip():
    """API client supports trip cancellation."""
    api_path = os.path.join(CLIENT_DIR, "src", "lib", "api.ts")
    with open(api_path) as f:
        content = f.read()
    assert "cancelTrip" in content
    assert "PATCH" in content


def test_page_has_settings_and_detail_views():
    """Main page includes Settings and TripDetail views."""
    page_path = os.path.join(CLIENT_DIR, "src", "app", "page.tsx")
    with open(page_path) as f:
        content = f.read()
    assert "Settings" in content
    assert "TripDetail" in content
    assert "getSavedPreferences" in content
    assert "handleCancelTrip" in content


# ── Tier 3: Mobile polish (PWA) ──────────────────────────────────────────────


def test_bottom_nav_has_mobile_tabs():
    """BottomNav provides mobile tab navigation with touch targets."""
    nav_path = os.path.join(CLIENT_DIR, "src", "components", "BottomNav.tsx")
    with open(nav_path) as f:
        content = f.read()
    assert "btm-nav" in content
    assert "lg:hidden" in content
    assert "min-h-touch" in content
    assert "onTabChange" in content
    assert "safe-area-bottom" in content


def test_install_prompt_has_beforeinstallprompt():
    """InstallPrompt handles beforeinstallprompt and iOS guidance."""
    prompt_path = os.path.join(CLIENT_DIR, "src", "components", "InstallPrompt.tsx")
    with open(prompt_path) as f:
        content = f.read()
    assert "beforeinstallprompt" in content
    assert "isIos" in content
    assert "isStandalone" in content
    assert "handleInstall" in content
    assert "handleDismiss" in content
    assert "Add to Home Screen" in content


def test_offline_page_exists():
    """Offline fallback page exists for service worker."""
    offline_path = os.path.join(CLIENT_DIR, "public", "offline.html")
    assert os.path.isfile(offline_path)
    with open(offline_path) as f:
        content = f.read()
    assert "offline" in content.lower()
    assert "cached-trips" in content


def test_globals_css_has_mobile_utilities():
    """globals.css has safe-area insets, touch targets, and bottom nav styles."""
    css_path = os.path.join(CLIENT_DIR, "src", "app", "globals.css")
    with open(css_path) as f:
        content = f.read()
    assert "safe-area-inset-bottom" in content
    assert "min-h-touch" in content
    assert "btm-nav" in content
    assert "mobile-safe-bottom" in content
    assert "-webkit-tap-highlight-color" in content


def test_layout_has_viewport_fit_cover():
    """Layout sets viewport-fit cover for notched devices."""
    layout_path = os.path.join(CLIENT_DIR, "src", "app", "layout.tsx")
    with open(layout_path) as f:
        content = f.read()
    assert "viewportFit" in content
    assert "cover" in content
    assert "black-translucent" in content
    assert "safe-area-top" in content


def test_next_config_has_offline_fallback():
    """next.config.js configures offline fallback and runtime caching."""
    config_path = os.path.join(CLIENT_DIR, "next.config.js")
    with open(config_path) as f:
        content = f.read()
    assert "fallbacks" in content
    assert "offline.html" in content
    assert "runtimeCaching" in content
    assert "NetworkFirst" in content
    assert "api-trip-detail" in content


def test_manifest_has_shortcuts():
    """manifest.json includes app shortcuts for quick actions."""
    manifest_path = os.path.join(CLIENT_DIR, "public", "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    assert "shortcuts" in manifest
    assert len(manifest["shortcuts"]) >= 1
    assert manifest["shortcuts"][0]["name"] == "Plan a Trip"


def test_page_has_mobile_layout():
    """Main page uses BottomNav, InstallPrompt, and swipe gestures."""
    page_path = os.path.join(CLIENT_DIR, "src", "app", "page.tsx")
    with open(page_path) as f:
        content = f.read()
    assert "BottomNav" in content
    assert "InstallPrompt" in content
    assert "mobileTab" in content
    assert "onTouchStart" in content
    assert "onTouchEnd" in content
    assert "mobile-safe-bottom" in content
    assert "lg:hidden" in content


def test_touch_targets_on_key_components():
    """Key interactive components use min-h-touch for 44px tap targets."""
    for name in ["TripForm.tsx", "TripList.tsx", "TripDetail.tsx", "Settings.tsx"]:
        path = os.path.join(CLIENT_DIR, "src", "components", name)
        with open(path) as f:
            content = f.read()
        assert "min-h-touch" in content, f"{name} should use min-h-touch for touch targets"


def test_env_example_exists():
    """A .env.example file exists at the repo root."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
    assert os.path.isfile(env_path), ".env.example must exist at repo root"
    with open(env_path) as f:
        content = f.read()
    assert "ANTHROPIC_API_KEY" in content
    assert "AUTH_SECRET" in content
    assert "VAPID_PUBLIC_KEY" in content
