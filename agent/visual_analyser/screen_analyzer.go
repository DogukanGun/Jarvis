package main

import (
	"fmt"
	"log"
)

// ScreenAnalyzer handles screen analysis operations
type ScreenAnalyzer struct {
	visionService *VisionService
}

// NewScreenAnalyzer creates a new screen analyzer
func NewScreenAnalyzer() *ScreenAnalyzer {
	return &ScreenAnalyzer{
		visionService: NewVisionService(),
	}
}

// AnalyzeScreen processes screen analysis requests
func (sa *ScreenAnalyzer) AnalyzeScreen(req AnalyzeScreenRequest) (*AnalyzeScreenResponse, error) {
	log.Printf("Processing screen analysis: action=%s, query=%s", req.Action, req.Query)

	switch req.Action {
	case "find_element":
		return sa.findElement(req)
	case "find_coordinates":
		return sa.findCoordinates(req)
	case "detect_text":
		return sa.detectText(req)
	case "describe_screen":
		return sa.describeScreen(req)
	default:
		return nil, fmt.Errorf("unsupported action: %s", req.Action)
	}
}

// findElement finds a UI element and returns its details
func (sa *ScreenAnalyzer) findElement(req AnalyzeScreenRequest) (*AnalyzeScreenResponse, error) {
	if req.Query == "" {
		return nil, fmt.Errorf("query is required for find_element action")
	}

	if req.Screenshot == "" {
		return nil, fmt.Errorf("screenshot is required")
	}

	elements, err := sa.visionService.FindElement(req.Screenshot, req.Query)
	if err != nil {
		return &AnalyzeScreenResponse{
			Success: false,
			Action:  req.Action,
			Error:   err.Error(),
		}, nil
	}

	return &AnalyzeScreenResponse{
		Success:  true,
		Action:   req.Action,
		Elements: elements,
	}, nil
}

// findCoordinates is an alias for findElement (focused on getting coordinates)
func (sa *ScreenAnalyzer) findCoordinates(req AnalyzeScreenRequest) (*AnalyzeScreenResponse, error) {
	return sa.findElement(req)
}

// detectText extracts all text from the screenshot
func (sa *ScreenAnalyzer) detectText(req AnalyzeScreenRequest) (*AnalyzeScreenResponse, error) {
	if req.Screenshot == "" {
		return nil, fmt.Errorf("screenshot is required")
	}

	textContent, err := sa.visionService.DetectText(req.Screenshot)
	if err != nil {
		return &AnalyzeScreenResponse{
			Success: false,
			Action:  req.Action,
			Error:   err.Error(),
		}, nil
	}

	description := fmt.Sprintf("Detected %d text elements", len(textContent))
	if len(textContent) > 0 {
		description = "Text detected:\n"
		for _, text := range textContent {
			description += "- " + text + "\n"
		}
	}

	return &AnalyzeScreenResponse{
		Success:     true,
		Action:      req.Action,
		Description: description,
	}, nil
}

// describeScreen provides full screen description
func (sa *ScreenAnalyzer) describeScreen(req AnalyzeScreenRequest) (*AnalyzeScreenResponse, error) {
	if req.Screenshot == "" {
		return nil, fmt.Errorf("screenshot is required")
	}

	description, err := sa.visionService.DescribeScreen(req.Screenshot)
	if err != nil {
		return &AnalyzeScreenResponse{
			Success: false,
			Action:  req.Action,
			Error:   err.Error(),
		}, nil
	}

	return &AnalyzeScreenResponse{
		Success:     true,
		Action:      req.Action,
		Description: description,
	}, nil
}

// GetCapabilities returns the analyzer capabilities
func (sa *ScreenAnalyzer) GetCapabilities() map[string][]string {
	return map[string][]string{
		"Screen Analysis": {
			"Find UI elements (buttons, fields, menus)",
			"Detect element coordinates for clicking",
			"Extract text from screenshots (OCR)",
			"Describe screen layout and content",
			"Identify applications and windows",
		},
		"Supported Actions": {
			"find_element - Find specific UI element",
			"find_coordinates - Get coordinates for element",
			"detect_text - Extract all visible text",
			"describe_screen - Full screen description",
		},
	}
}
