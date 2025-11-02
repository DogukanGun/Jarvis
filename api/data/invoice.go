package data

import "time"

type Invoice struct {
	ID                   string    `json:"id"`
	UserID               string    `json:"user_id"`
	Month                int       `json:"month"`
	Year                 int       `json:"year"`
	Amount               float64   `json:"amount"`
	PaymentValidationUrl string    `json:"payment_validation_url"`
	IsPaid               bool      `json:"is_paid"`
	CreatedAt            time.Time `json:"created_at"`
	LastActive           time.Time `json:"last_active"`
	PaidAt               *time.Time `json:"paid_at,omitempty"`
}

func (i *Invoice) GetID() string {
	return i.ID
}

func (i *Invoice) SetID(id string) {
	i.ID = id
}

func (i *Invoice) SetCreatedAt(t time.Time) {
	i.CreatedAt = t
}

func (i *Invoice) SetLastActive(t time.Time) {
	i.LastActive = t
}
