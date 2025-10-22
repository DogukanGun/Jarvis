package jarvisTools

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"time"

	"github.com/tmc/langchaingo/tools"
)

type CommitToGitTool struct{}

func (t CommitToGitTool) Name() string {
	return "commit_to_git"
}

func (t CommitToGitTool) Description() string {
	return "Commit changes to git repository. Input should be JSON with 'message', optional 'files' array, and optional 'add_all' boolean."
}

func (t CommitToGitTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		Message string   `json:"message"`
		Files   []string `json:"files"`
		AddAll  bool     `json:"add_all"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	return commitToGit(args.Message, args.Files, args.AddAll)
}

type CreatePullRequestTool struct{}

func (t CreatePullRequestTool) Name() string {
	return "create_pull_request"
}

func (t CreatePullRequestTool) Description() string {
	return "Create a pull request on GitHub/GitLab. Input should be JSON with 'title', 'body', optional 'base_branch', optional 'head_branch', and optional 'repository' fields."
}

func (t CreatePullRequestTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		Title      string `json:"title"`
		Body       string `json:"body"`
		BaseBranch string `json:"base_branch"`
		HeadBranch string `json:"head_branch"`
		Repository string `json:"repository"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	if args.BaseBranch == "" {
		args.BaseBranch = "main"
	}

	return createPullRequest(args.Title, args.Body, args.BaseBranch, args.HeadBranch, args.Repository)
}

type CommentDiffTool struct{}

func (t CommentDiffTool) Name() string {
	return "comment_diff"
}

func (t CommentDiffTool) Description() string {
	return "Add comments to a diff or pull request. Input should be JSON with 'comment', optional 'file_path', optional 'line_number', optional 'pr_number', and optional 'repository' fields."
}

func (t CommentDiffTool) Call(ctx context.Context, input string) (string, error) {
	var args struct {
		Comment    string `json:"comment"`
		FilePath   string `json:"file_path"`
		LineNumber int    `json:"line_number"`
		PRNumber   int    `json:"pr_number"`
		Repository string `json:"repository"`
	}

	if err := json.Unmarshal([]byte(input), &args); err != nil {
		return "", fmt.Errorf("invalid input JSON: %v", err)
	}

	return commentDiff(args.Comment, args.FilePath, args.LineNumber, args.PRNumber, args.Repository)
}

func commitToGit(message string, files []string, addAll bool) (string, error) {
	var output strings.Builder

	if addAll {
		cmd := exec.Command("git", "add", ".")
		out, err := cmd.CombinedOutput()
		if err != nil {
			return "", fmt.Errorf("failed to add files: %v", err)
		}
		output.WriteString("Added all files\n")
		output.WriteString(string(out))
	} else if len(files) > 0 {
		args := []string{"add"}
		args = append(args, files...)
		cmd := exec.Command("git", args...)
		out, err := cmd.CombinedOutput()
		if err != nil {
			return "", fmt.Errorf("failed to add specified files: %v", err)
		}
		output.WriteString("Added specified files\n")
		output.WriteString(string(out))
	}

	cmd := exec.Command("git", "commit", "-m", message)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return output.String(), fmt.Errorf("failed to commit: %v", err)
	}

	output.WriteString("Committed successfully\n")
	output.WriteString(string(out))
	return output.String(), nil
}

func createPullRequest(title, body, baseBranch, headBranch, repository string) (string, error) {
	if headBranch == "" {
		cmd := exec.Command("git", "branch", "--show-current")
		out, err := cmd.Output()
		if err != nil {
			return "", fmt.Errorf("failed to get current branch: %v", err)
		}
		headBranch = strings.TrimSpace(string(out))
	}

	var cmd *exec.Cmd
	if repository != "" {
		cmd = exec.Command("gh", "pr", "create",
			"--title", title,
			"--body", body,
			"--base", baseBranch,
			"--head", headBranch,
			"--repo", repository)
	} else {
		cmd = exec.Command("gh", "pr", "create",
			"--title", title,
			"--body", body,
			"--base", baseBranch,
			"--head", headBranch)
	}

	done := make(chan error, 1)
	var output []byte

	go func() {
		var err error
		output, err = cmd.CombinedOutput()
		done <- err
	}()

	select {
	case err := <-done:
		if err != nil {
			return string(output), fmt.Errorf("failed to create pull request: %v", err)
		}
		return string(output), nil
	case <-time.After(30 * time.Second):
		if cmd.Process != nil {
			cmd.Process.Kill()
		}
		return "", fmt.Errorf("pull request creation timed out")
	}
}

func commentDiff(comment, filePath string, lineNumber, prNumber int, repository string) (string, error) {
	if prNumber > 0 {
		var cmd *exec.Cmd
		if repository != "" {
			cmd = exec.Command("gh", "pr", "comment", fmt.Sprintf("%d", prNumber),
				"--body", comment,
				"--repo", repository)
		} else {
			cmd = exec.Command("gh", "pr", "comment", fmt.Sprintf("%d", prNumber),
				"--body", comment)
		}

		output, err := cmd.CombinedOutput()
		if err != nil {
			return string(output), fmt.Errorf("failed to comment on pull request: %v", err)
		}
		return string(output), nil
	}

	statusCmd := exec.Command("git", "status", "--porcelain")
	statusOut, err := statusCmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to check git status: %v", err)
	}

	if len(statusOut) == 0 {
		return "No changes to comment on", nil
	}

	diffCmd := exec.Command("git", "diff", "--cached")
	if filePath != "" {
		diffCmd = exec.Command("git", "diff", "--cached", filePath)
	}

	diffOut, err := diffCmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get diff: %v", err)
	}

	result := fmt.Sprintf("Comment: %s\n\nDiff:\n%s", comment, string(diffOut))
	return result, nil
}

func GetCommunicationTools() []tools.Tool {
	return []tools.Tool{
		CommitToGitTool{},
		CreatePullRequestTool{},
		CommentDiffTool{},
	}
}
