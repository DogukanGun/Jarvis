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

// VisualAnalyserTool provides screen analysis capabilities
type VisualAnalyserTool struct {
	analyserURL string
	client      *http.Client
	guiControl  *GUIControlTool
}

func NewVisualAnalyserTool() *VisualAnalyserTool {
	analyserURL := os.Getenv("VISUAL_ANALYSER_URL")
	if analyserURL == "" {
		analyserURL = "http://127.0.0.1:8081"
	}

	return &VisualAnalyserTool{
		analyserURL: analyserURL,
		client: &http.Client{
			Timeout: 2 * time.Minute, // Vision models need more time
		},
		guiControl: NewGUIControlTool(),
	}
}

func (t VisualAnalyserTool) Name() string {
	return "analyze_screen"
}

func (t VisualAnalyserTool) Description() string {
	return `Analyze the screen to find UI elements and get their coordinates. Input should be JSON with action and parameters.

Available actions:
- find_element: Find specific UI element by description. Params: {"query": "submit button"}
- find_coordinates: Get coordinates for clicking an element. Params: {"query": "login field"}
- detect_text: Extract all visible text from screen
- describe_screen: Get full description of screen layout and content

Returns element coordinates, confidence, and descriptions.

Example input: {"action": "find_element", "query": "submit button"}`
}

func (t VisualAnalyserTool) Call(ctx context.Context, input string) (string, error) {
	// Parse input JSON
	var analyseRequest map[string]interface{}
	if err := json.Unmarshal([]byte(input), &analyseRequest); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	// Validate action field
	action, ok := analyseRequest["action"].(string)
	if !ok {
		return "", fmt.Errorf("missing or invalid 'action' field")
	}

	// First, take a screenshot
	screenshotAction := map[string]interface{}{
		"action": "screenshot",
	}
	screenshotJSON, _ := json.Marshal(screenshotAction)
	_, err := t.guiControl.Call(ctx, string(screenshotJSON))
	if err != nil {
		return "", fmt.Errorf("failed to take screenshot: %v", err)
	}

	// Extract base64 image from GUI daemon response
	// The GUI daemon returns it through formatResponse, but we need the raw data
	// Let's get it directly
	daemonResp, err := t.guiControl.sendAction(screenshotAction)
	if err != nil {
		return "", fmt.Errorf("failed to get screenshot data: %v", err)
	}

	var screenshot string
	if data, ok := daemonResp["data"].(map[string]interface{}); ok {
		if image, ok := data["image"].(string); ok {
			screenshot = image
		}
	}

	if screenshot == "" {
		return "", fmt.Errorf("failed to extract screenshot image")
	}

	// Build request for visual analyser
	analyseRequest["screenshot"] = screenshot

	// Send request to visual analyser
	response, err := t.sendAnalyseRequest(analyseRequest)
	if err != nil {
		return "", err
	}

	// Format response based on action type
	return t.formatResponse(action, response)
}

// sendAnalyseRequest sends request to visual analyser service
func (t *VisualAnalyserTool) sendAnalyseRequest(request map[string]interface{}) (map[string]interface{}, error) {
	// Marshal request
	requestBody, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	// Create request
	req, err := http.NewRequest("POST", t.analyserURL+"/analyze", bytes.NewBuffer(requestBody))
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
		return nil, fmt.Errorf("visual analyser error: %s", errMsg)
	}

	return result, nil
}

// formatResponse formats the response based on action type
func (t *VisualAnalyserTool) formatResponse(action string, response map[string]interface{}) (string, error) {
	switch action {
	case "find_element", "find_coordinates":
		if elements, ok := response["elements"].([]interface{}); ok {
			if len(elements) == 0 {
				return "No elements found matching the query", nil
			}

			// Format elements
			result := fmt.Sprintf("Found %d element(s):\n", len(elements))
			for i, elem := range elements {
				elemMap, ok := elem.(map[string]interface{})
				if !ok {
					continue
				}

				name := elemMap["name"]
				coords := elemMap["coordinates"]
				confidence := elemMap["confidence"]
				description := elemMap["description"]

				coordsMap, ok := coords.(map[string]interface{})
				if !ok {
					continue
				}

				x := coordsMap["x"]
				y := coordsMap["y"]

				result += fmt.Sprintf("\n%d. %s\n", i+1, name)
				result += fmt.Sprintf("   Coordinates: (%v, %v)\n", x, y)
				result += fmt.Sprintf("   Confidence: %.2f\n", confidence)
				if description != nil && description != "" {
					result += fmt.Sprintf("   Description: %s\n", description)
				}
			}

			return result, nil
		}
		return "No elements found", nil

	case "detect_text":
		if description, ok := response["description"].(string); ok {
			return description, nil
		}
		return "Text detection completed", nil

	case "describe_screen":
		if description, ok := response["description"].(string); ok {
			return description, nil
		}
		return "Screen description completed", nil

	default:
		return fmt.Sprintf("Analysis action '%s' completed", action), nil
	}
}

// FindElementTool - Specialized tool for finding UI elements
type FindElementTool struct {
	analyser *VisualAnalyserTool
}

func (t FindElementTool) Name() string {
	return "find_element"
}

func (t FindElementTool) Description() string {
	return `Find a specific UI element on the screen by description. Returns coordinates for clicking.
Input should be JSON with 'query' field describing the element to find.
Example: {"query": "submit button"} or {"query": "username text field"}`
}

func (t FindElementTool) Call(ctx context.Context, input string) (string, error) {
	var params struct {
		Query string `json:"query"`
	}

	if err := json.Unmarshal([]byte(input), &params); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	if params.Query == "" {
		return "", fmt.Errorf("query field is required")
	}

	request := map[string]interface{}{
		"action": "find_element",
		"query":  params.Query,
	}

	requestJSON, _ := json.Marshal(request)
	return t.analyser.Call(ctx, string(requestJSON))
}

// DetectTextTool - Specialized tool for text detection
type DetectTextTool struct {
	analyser *VisualAnalyserTool
}

func (t DetectTextTool) Name() string {
	return "detect_text"
}

func (t DetectTextTool) Description() string {
	return `Extract all visible text from the current screen using OCR.
Returns a list of all text elements found on screen.
No input required (use empty JSON {}).`
}

func (t DetectTextTool) Call(ctx context.Context, input string) (string, error) {
	request := map[string]interface{}{
		"action": "detect_text",
	}

	requestJSON, _ := json.Marshal(request)
	return t.analyser.Call(ctx, string(requestJSON))
}

// DescribeScreenTool - Specialized tool for screen description
type DescribeScreenTool struct {
	analyser *VisualAnalyserTool
}

func (t DescribeScreenTool) Name() string {
	return "describe_screen"
}

func (t DescribeScreenTool) Description() string {
	return `Get a detailed description of what's currently on the screen.
Describes the application, UI layout, available actions, and element positions.
No input required (use empty JSON {}).`
}

func (t DescribeScreenTool) Call(ctx context.Context, input string) (string, error) {
	request := map[string]interface{}{
		"action": "describe_screen",
	}

	requestJSON, _ := json.Marshal(request)
	return t.analyser.Call(ctx, string(requestJSON))
}

// GetVisualAnalyserTools returns all visual analyser tools
func GetVisualAnalyserTools() []tools.Tool {
	analyser := NewVisualAnalyserTool()

	return []tools.Tool{
		analyser,
		FindElementTool{analyser: analyser},
		DetectTextTool{analyser: analyser},
		DescribeScreenTool{analyser: analyser},
	}
}
