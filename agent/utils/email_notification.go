package utils

import (
	"bytes"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"html"
	"net/smtp"
	"os"
	"strings"
	"time"
)

// SendStyledEmail sends an HTML email via Gmail SMTP with a plain-text fallback.
// from:        your Gmail address (e.g., "you@gmail.com")
// appPassword: Gmail App Password (16 chars)
// to:          list of recipient emails
// subject:     email subject (ASCII; for UTF-8 subjects, add RFC2047 encoding)
// message:     your message body (plain text, newlines are preserved)
func SendStyledEmail(from string, to []string, subject, message string) error {
	// SMTP config
	host := "smtp.gmail.com"
	addr := host + ":587"

	// Prepare IDs & headers
	now := time.Now()
	messageID := fmt.Sprintf("<%d.%s@%s>", now.UnixNano(), randomToken(8), "local")
	dateHeader := now.Format(time.RFC1123Z)

	// Build a multipart/alternative message (plain text + HTML)
	boundary := "bnd_" + randomToken(12)

	// Plain text part (use the raw message)
	plainPart := message

	// HTML part (escape + convert newlines to <br>)
	escaped := html.EscapeString(message)
	htmlPart := buildHTMLTemplate(strings.ReplaceAll(escaped, "\n", "<br>"))

	// RFC 5322 headers
	var buf bytes.Buffer
	writeHeader(&buf, "From", from)
	writeHeader(&buf, "To", strings.Join(to, ", "))
	writeHeader(&buf, "Subject", subject)
	writeHeader(&buf, "Date", dateHeader)
	writeHeader(&buf, "Message-ID", messageID)
	writeHeader(&buf, "MIME-Version", "1.0")
	writeHeader(&buf, "Content-Type", fmt.Sprintf(`multipart/alternative; boundary="%s"`, boundary))
	buf.WriteString("\r\n")

	// Plain text section
	fmt.Fprintf(&buf, "--%s\r\n", boundary)
	buf.WriteString("Content-Type: text/plain; charset=UTF-8\r\n")
	buf.WriteString("Content-Transfer-Encoding: 7bit\r\n\r\n")
	buf.WriteString(plainPart + "\r\n")

	// HTML section
	fmt.Fprintf(&buf, "--%s\r\n", boundary)
	buf.WriteString("Content-Type: text/html; charset=UTF-8\r\n")
	buf.WriteString("Content-Transfer-Encoding: 7bit\r\n\r\n")
	buf.WriteString(htmlPart + "\r\n")

	// Closing boundary
	fmt.Fprintf(&buf, "--%s--\r\n", boundary)

	// Auth & send
	pssw := os.Getenv("EMAIL_PASSWORD")
	auth := smtp.PlainAuth("", from, pssw, host)
	return smtp.SendMail(addr, auth, from, to, buf.Bytes())
}

func writeHeader(buf *bytes.Buffer, k, v string) {
	buf.WriteString(k + ": " + v + "\r\n")
}

func randomToken(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}

// Simple, clean HTML card with inline styles (plays nice in Gmail/Outlook)
func buildHTMLTemplate(body string) string {
	return `<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title></title>
</head>
<body style="margin:0;padding:0;background:#f5f7fb;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f7fb;">
    <tr>
      <td align="center" style="padding:24px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" 
               style="max-width:640px;background:#ffffff;border-radius:12px;overflow:hidden;
                      box-shadow:0 4px 16px rgba(0,0,0,0.06);font-family:Arial,Helvetica,sans-serif;">
          <tr>
            <td style="background:#111827;color:#ffffff;padding:18px 20px;font-size:18px;font-weight:700;">
              Notification
            </td>
          </tr>
          <tr>
            <td style="padding:24px 20px;color:#111827;font-size:15px;line-height:1.6;">
              ` + body + `
            </td>
          </tr>
          <tr>
            <td style="padding:10px 20px 22px;color:#6b7280;font-size:12px;border-top:1px solid #f0f2f6;">
              Sent via Go · ` + time.Now().Format("2006-01-02 15:04 MST") + `
            </td>
          </tr>
        </table>
        <div style="color:#9ca3af;font-size:12px;margin-top:12px;">
          If this email looks broken, try viewing it in a modern email client.
        </div>
      </td>
    </tr>
  </table>
</body>
</html>`
}
