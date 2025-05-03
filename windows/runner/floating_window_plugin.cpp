#include <windows.h>
#include <string>
#include <map>
#include <functional>

#define IDC_TIMER_TEXT 101
#define IDC_PLAY_PAUSE_BUTTON 102
#define IDC_RESET_BUTTON 103
#define IDC_FULLSCREEN_BUTTON 104

#define WINDOW_WIDTH 160
#define WINDOW_HEIGHT 100

HWND g_FloatingWindow = NULL;
HWND g_TimerText = NULL;
HWND g_PlayPauseButton = NULL;
HWND g_ResetButton = NULL;
HWND g_FullscreenButton = NULL;
HFONT g_TimerFont = NULL;
bool g_IsTimerRunning = false;

std::map<std::string, std::function<void()>> g_Callbacks;

LRESULT CALLBACK FloatingWindowProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam) {
    switch (message) {
        case WM_CREATE:
        {
            g_TimerText = CreateWindow(
                L"STATIC",
                L"00:00",
                WS_CHILD | WS_VISIBLE | SS_CENTER,
                10, 10, WINDOW_WIDTH-20, 40,
                hwnd, (HMENU)IDC_TIMER_TEXT,
                ((LPCREATESTRUCT)lParam)->hInstance, NULL
            );
            
            g_PlayPauseButton = CreateWindow(
                L"BUTTON",
                L"▶",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                20, 60, 30, 30,
                hwnd, (HMENU)IDC_PLAY_PAUSE_BUTTON,
                ((LPCREATESTRUCT)lParam)->hInstance, NULL
            );
            
            g_ResetButton = CreateWindow(
                L"BUTTON",
                L"↺",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                60, 60, 30, 30,
                hwnd, (HMENU)IDC_RESET_BUTTON,
                ((LPCREATESTRUCT)lParam)->hInstance, NULL
            );
            
            g_FullscreenButton = CreateWindow(
                L"BUTTON",
                L"⛶",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                100, 60, 30, 30,
                hwnd, (HMENU)IDC_FULLSCREEN_BUTTON,
                ((LPCREATESTRUCT)lParam)->hInstance, NULL
            );
            
            g_TimerFont = CreateFont(
                32, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                DEFAULT_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"Arial"
            );
            
            SendMessage(g_TimerText, WM_SETFONT, (WPARAM)g_TimerFont, TRUE);
            
            return 0;
        }
        
        case WM_COMMAND:
        {
            int wmId = LOWORD(wParam);
            
            switch (wmId) {
                case IDC_PLAY_PAUSE_BUTTON:
                    if (g_Callbacks.find("playPause") != g_Callbacks.end()) {
                        g_Callbacks["playPause"]();
                    }
                    return 0;
                    
                case IDC_RESET_BUTTON:
                    if (g_Callbacks.find("reset") != g_Callbacks.end()) {
                        g_Callbacks["reset"]();
                    }
                    return 0;
                    
                case IDC_FULLSCREEN_BUTTON:
                    if (g_Callbacks.find("fullscreen") != g_Callbacks.end()) {
                        g_Callbacks["fullscreen"]();
                    }
                    return 0;
            }
            break;
        }
        
        case WM_LBUTTONDOWN:
        {
            ReleaseCapture();
            SendMessage(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0);
            return 0;
        }
        
        case WM_CLOSE:
            ShowWindow(hwnd, SW_HIDE);
            return 0;
            
        case WM_DESTROY:
            if (g_TimerFont) {
                DeleteObject(g_TimerFont);
                g_TimerFont = NULL;
            }
            g_FloatingWindow = NULL;
            g_TimerText = NULL;
            g_PlayPauseButton = NULL;
            g_ResetButton = NULL;
            g_FullscreenButton = NULL;
            return 0;
    }
    
    return DefWindowProc(hwnd, message, wParam, lParam);
}

extern "C" __declspec(dllexport) bool CreateFloatingWindow(HINSTANCE hInstance) {
    WNDCLASSEX wcex = {0};
    wcex.cbSize = sizeof(WNDCLASSEX);
    wcex.style = CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc = FloatingWindowProc;
    wcex.hInstance = hInstance;
    wcex.hCursor = LoadCursor(NULL, IDC_ARROW);
    wcex.hbrBackground = (HBRUSH)(COLOR_WINDOW+1);
    wcex.lpszClassName = L"PracTwiceFloatingWindow";
    
    if (!RegisterClassEx(&wcex)) {
        return false;
    }
    
    g_FloatingWindow = CreateWindowEx(
        WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
        L"PracTwiceFloatingWindow",
        L"Timer",
        WS_POPUP | WS_BORDER | WS_VISIBLE,
        GetSystemMetrics(SM_CXSCREEN) - WINDOW_WIDTH - 20,
        20,
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
        NULL,
        NULL,
        hInstance,
        NULL
    );
    
    if (!g_FloatingWindow) {
        return false;
    }
    
    SetLayeredWindowAttributes(g_FloatingWindow, 0, 230, LWA_ALPHA);
    
    ShowWindow(g_FloatingWindow, SW_SHOW);
    UpdateWindow(g_FloatingWindow);
    
    return true;
}

extern "C" __declspec(dllexport) void CloseFloatingWindow() {
    if (g_FloatingWindow) {
        DestroyWindow(g_FloatingWindow);
    }
}

extern "C" __declspec(dllexport) void UpdateTimerDisplay(const char* timeText) {
    if (g_TimerText) {
        int size = MultiByteToWideChar(CP_UTF8, 0, timeText, -1, NULL, 0);
        wchar_t* wTimeText = new wchar_t[size];
        MultiByteToWideChar(CP_UTF8, 0, timeText, -1, wTimeText, size);
        
        SetWindowText(g_TimerText, wTimeText);
        
        delete[] wTimeText;
    }
}

extern "C" __declspec(dllexport) void UpdatePlayPauseButton(bool isRunning) {
    if (g_PlayPauseButton) {
        g_IsTimerRunning = isRunning;
        SetWindowText(g_PlayPauseButton, isRunning ? L"⏸" : L"▶");
    }
}

extern "C" __declspec(dllexport) void RegisterPlayPauseCallback(std::function<void()> callback) {
    g_Callbacks["playPause"] = callback;
}

extern "C" __declspec(dllexport) void RegisterResetCallback(std::function<void()> callback) {
    g_Callbacks["reset"] = callback;
}

extern "C" __declspec(dllexport) void RegisterFullscreenCallback(std::function<void()> callback) {
    g_Callbacks["fullscreen"] = callback;
}