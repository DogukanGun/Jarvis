package jarvisTools

import (
	"context"
	"jarvis/agent/utils"
)

type EmailTool struct{}

func (t EmailTool) Name() string {
	return "email_tool"
}

func (t EmailTool) Description() string {
	return "This tool must be used to send an email to owner as the result of what is wanted, if specifically the owner wants"
}

func (t EmailTool) Call(ctx context.Context, input string) (string, error) {
	from := "dan_jarvis@gmail.com"
	to := []string{"dogukangundogan5@gmail.com"} // TODO: Replace with owner's email
	subject := "Jarvis Agent Notification"

	err := utils.SendStyledEmail(from, to, subject, input)
	if err != nil {
		return "", err
	}

	return "Email sent successfully", nil
}
