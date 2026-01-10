package jarvisTools

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"time"

	"github.com/tmc/langchaingo/tools"
)

// GUIControlTool provides GUI automation capabilities
type GUIControlTool struct {
	daemonURL string
	client    *http.Client
}

func NewGUIControlTool() *GUIControlTool {
	daemonURL := os.Getenv("GUI_DAEMON_URL")
	if daemonURL == "" {
		daemonURL = "http://gui-daemon:9990"
	}

	return &GUIControlTool{
		daemonURL: daemonURL,
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (t GUIControlTool) Name() string {
	return "gui_control"
}

func (t GUIControlTool) Description() string {
	return `Control the computer GUI (mouse, keyboard, screen). Input should be JSON with action and parameters.

Available actions:
- move_mouse: Move cursor to coordinates. Params: {"coordinates": {"x": 100, "y": 200}}
- click_mouse: Click mouse button. Params: {"button": "left", "coordinates": {"x": 100, "y": 200}, "clickCount": 1}
- drag_mouse: Drag mouse along path. Params: {"path": [{"x": 100, "y": 100}, {"x": 200, "y": 200}], "button": "left"}
- scroll: Scroll in direction. Params: {"direction": "down", "scrollCount": 3}
- type_text: Type text string. Params: {"text": "Hello World", "delay": 0}
- type_keys: Press key combination. Params: {"keys": ["ctrl", "c"]}
- paste_text: Paste text via clipboard. Params: {"text": "Hello World"}
- screenshot: Capture screen (returns base64 PNG)
- cursor_position: Get current cursor position
- application: Launch application. Params: {"application": "firefox"} (firefox|vscode|terminal|directory)
- write_file: Write file. Params: {"path": "test.txt", "data": "base64encodeddata"}
- read_file: Read file. Params: {"path": "test.txt"}
- wait: Delay execution. Params: {"duration": 1000} (milliseconds)

Example input: {"action": "type_text", "text": "Hello World"}`
}

func (t GUIControlTool) Call(ctx context.Context, input string) (string, error) {
	// Parse input JSON
	var actionRequest map[string]interface{}
	if err := json.Unmarshal([]byte(input), &actionRequest); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	// Validate action field
	action, ok := actionRequest["action"].(string)
	if !ok {
		return "", fmt.Errorf("missing or invalid 'action' field")
	}

	// Send request to GUI daemon
	response, err := t.sendAction(actionRequest)
	if err != nil {
		return "", err
	}

	// Format response based on action type
	return t.formatResponse(action, response)
}

// sendAction sends action to GUI daemon
func (t *GUIControlTool) sendAction(action map[string]interface{}) (map[string]interface{}, error) {
	// Marshal request
	requestBody, err := json.Marshal(action)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	// Create request
	req, err := http.NewRequest("POST", t.daemonURL+"/computer-use", bytes.NewBuffer(requestBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")

	// Send request
	resp, err := t.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	// Read response
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	// Parse response
	var result map[string]interface{}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, fmt.Errorf("failed to parse response: %v", err)
	}

	// Check for errors
	if success, ok := result["success"].(bool); ok && !success {
		errMsg := "unknown error"
		if errStr, ok := result["error"].(string); ok {
			errMsg = errStr
		}
		return nil, fmt.Errorf("GUI daemon error: %s", errMsg)
	}

	return result, nil
}

// formatResponse formats the response based on action type
func (t *GUIControlTool) formatResponse(action string, response map[string]interface{}) (string, error) {
	switch action {
	case "screenshot":
		if data, ok := response["data"].(map[string]interface{}); ok {
			if image, ok := data["image"].(string); ok {
				return fmt.Sprintf("Screenshot captured successfully (base64 length: %d)", len(image)), nil
			}
		}
		return "Screenshot captured successfully", nil

	case "cursor_position":
		if data, ok := response["data"].(map[string]interface{}); ok {
			x := data["x"]
			y := data["y"]
			return fmt.Sprintf("Cursor position: (%v, %v)", x, y), nil
		}
		return "Cursor position retrieved", nil

	case "read_file":
		if data, ok := response["data"].(map[string]interface{}); ok {
			name := data["name"]
			size := data["size"]
			mediaType := data["mediaType"]
			return fmt.Sprintf("File read successfully: %s (%v bytes, %s)", name, size, mediaType), nil
		}
		return "File read successfully", nil

	case "write_file":
		if data, ok := response["data"].(map[string]interface{}); ok {
			if message, ok := data["message"].(string); ok {
				return message, nil
			}
		}
		return "File written successfully", nil

	default:
		return fmt.Sprintf("Action '%s' executed successfully", action), nil
	}
}

// MouseMoveTool - Specialized tool for mouse movement
type MouseMoveTool struct {
	guiControl *GUIControlTool
}

func (t MouseMoveTool) Name() string {
	return "move_mouse"
}

func (t MouseMoveTool) Description() string {
	return "Move mouse cursor to specific coordinates. Input should be JSON with 'x' and 'y' fields."
}

func (t MouseMoveTool) Call(ctx context.Context, input string) (string, error) {
	var coords struct {
		X int `json:"x"`
		Y int `json:"y"`
	}

	if err := json.Unmarshal([]byte(input), &coords); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	action := map[string]interface{}{
		"action": "move_mouse",
		"coordinates": map[string]int{
			"x": coords.X,
			"y": coords.Y,
		},
	}

	actionJSON, _ := json.Marshal(action)
	return t.guiControl.Call(ctx, string(actionJSON))
}

// ClickMouseTool - Specialized tool for mouse clicking
type ClickMouseTool struct {
	guiControl *GUIControlTool
}

func (t ClickMouseTool) Name() string {
	return "click_mouse"
}

func (t ClickMouseTool) Description() string {
	return "Click mouse at current position or specified coordinates. Input should be JSON with optional 'x', 'y', 'button' (left/right/middle), and 'clickCount' fields."
}

func (t ClickMouseTool) Call(ctx context.Context, input string) (string, error) {
	var params struct {
		X          *int   `json:"x,omitempty"`
		Y          *int   `json:"y,omitempty"`
		Button     string `json:"button,omitempty"`
		ClickCount int    `json:"clickCount,omitempty"`
	}

	if err := json.Unmarshal([]byte(input), &params); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	// Set defaults
	if params.Button == "" {
		params.Button = "left"
	}
	if params.ClickCount == 0 {
		params.ClickCount = 1
	}

	action := map[string]interface{}{
		"action":     "click_mouse",
		"button":     params.Button,
		"clickCount": params.ClickCount,
	}

	if params.X != nil && params.Y != nil {
		action["coordinates"] = map[string]int{
			"x": *params.X,
			"y": *params.Y,
		}
	}

	actionJSON, _ := json.Marshal(action)
	return t.guiControl.Call(ctx, string(actionJSON))
}

// TypeTextTool - Specialized tool for typing text
type TypeTextTool struct {
	guiControl *GUIControlTool
}

func (t TypeTextTool) Name() string {
	return "type_text"
}

func (t TypeTextTool) Description() string {
	return "Type text on the keyboard. Input should be JSON with 'text' field and optional 'delay' (milliseconds between characters)."
}

func (t TypeTextTool) Call(ctx context.Context, input string) (string, error) {
	var params struct {
		Text  string `json:"text"`
		Delay int    `json:"delay,omitempty"`
	}

	if err := json.Unmarshal([]byte(input), &params); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	action := map[string]interface{}{
		"action": "type_text",
		"text":   params.Text,
		"delay":  params.Delay,
	}

	actionJSON, _ := json.Marshal(action)
	return t.guiControl.Call(ctx, string(actionJSON))
}

// ScreenshotTool - Specialized tool for taking screenshots
type ScreenshotTool struct {
	guiControl *GUIControlTool
}

func (t ScreenshotTool) Name() string {
	return "take_screenshot"
}

func (t ScreenshotTool) Description() string {
	return "Capture a screenshot of the current screen. Returns base64-encoded PNG image. No input required (use empty JSON {})."
}

func (t ScreenshotTool) Call(ctx context.Context, input string) (string, error) {
	action := map[string]interface{}{
		"action": "screenshot",
	}

	actionJSON, _ := json.Marshal(action)
	return t.guiControl.Call(ctx, string(actionJSON))
}

// GetGUITools returns all GUI control tools
func GetGUITools() []tools.Tool {
	guiControl := NewGUIControlTool()

	return []tools.Tool{
		guiControl,
		MouseMoveTool{guiControl: guiControl},
		ClickMouseTool{guiControl: guiControl},
		TypeTextTool{guiControl: guiControl},
		ScreenshotTool{guiControl: guiControl},
	}
}
