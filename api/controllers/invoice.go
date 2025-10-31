package controllers

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"jarvis/api/data"
	"jarvis/api/services"
)

type InvoiceController struct {
	invoiceManager *services.InvoiceManager
}

func NewInvoiceController(invoiceManager *services.InvoiceManager) *InvoiceController {
	return &InvoiceController{
		invoiceManager: invoiceManager,
	}
}

// CreateInvoiceRequest represents invoice creation data
type CreateInvoiceRequest struct {
	UserID               string  `json:"user_id" validate:"required"`
	Month                int     `json:"month" validate:"required,min=1,max=12"`
	Year                 int     `json:"year" validate:"required,min=2020"`
	Amount               float64 `json:"amount" validate:"required,min=0"`
	PaymentValidationUrl string  `json:"payment_validation_url" validate:"required,url"`
}

// InvoiceResponse represents invoice data for API responses
type InvoiceResponse struct {
	ID                   string     `json:"id"`
	UserID               string     `json:"user_id"`
	Month                int        `json:"month"`
	Year                 int        `json:"year"`
	Amount               float64    `json:"amount"`
	PaymentValidationUrl string     `json:"payment_validation_url"`
	IsPaid               bool       `json:"is_paid"`
	CreatedAt            time.Time  `json:"created_at"`
	LastActive           time.Time  `json:"last_active"`
	PaidAt               *time.Time `json:"paid_at,omitempty"`
}

// GenerateMonthlyInvoiceRequest represents monthly invoice generation data
type GenerateMonthlyInvoiceRequest struct {
	Month                int     `json:"month" validate:"required,min=1,max=12"`
	Year                 int     `json:"year" validate:"required,min=2020"`
	Amount               float64 `json:"amount" validate:"required,min=0"`
	PaymentValidationUrl string  `json:"payment_validation_url" validate:"required,url"`
}

// UpdateInvoiceRequest represents invoice update data
type UpdateInvoiceRequest struct {
	Amount               *float64 `json:"amount,omitempty" validate:"omitempty,min=0"`
	PaymentValidationUrl *string  `json:"payment_validation_url,omitempty" validate:"omitempty,url"`
}

func invoiceToResponse(invoice *data.Invoice) InvoiceResponse {
	return InvoiceResponse{
		ID:                   invoice.ID,
		UserID:               invoice.UserID,
		Month:                invoice.Month,
		Year:                 invoice.Year,
		Amount:               invoice.Amount,
		PaymentValidationUrl: invoice.PaymentValidationUrl,
		IsPaid:               invoice.IsPaid,
		CreatedAt:            invoice.CreatedAt,
		LastActive:           invoice.LastActive,
		PaidAt:               invoice.PaidAt,
	}
}

func invoicesToResponses(invoices []*data.Invoice) []InvoiceResponse {
	responses := make([]InvoiceResponse, len(invoices))
	for i, invoice := range invoices {
		responses[i] = invoiceToResponse(invoice)
	}
	return responses
}

// CreateInvoice creates a new invoice
// @Summary Create a new invoice
// @Description Creates a new invoice for a user
// @Tags Invoice Management
// @Accept json
// @Produce json
// @Param request body CreateInvoiceRequest true "Invoice creation data"
// @Param Authorization header string true "Bearer token"
// @Success 201 {object} InvoiceResponse "Invoice created successfully"
// @Failure 400 {object} ErrorResponse "Invalid request body"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 409 {object} ErrorResponse "Invoice already exists"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices [post]
func (ic *InvoiceController) CreateInvoice(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	var req CreateInvoiceRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if req.UserID == "" {
		sendError(w, "User ID is required", http.StatusBadRequest)
		return
	}
	if req.Month < 1 || req.Month > 12 {
		sendError(w, "Month must be between 1 and 12", http.StatusBadRequest)
		return
	}
	if req.Year < 2020 {
		sendError(w, "Year must be 2020 or later", http.StatusBadRequest)
		return
	}
	if req.Amount <= 0 {
		sendError(w, "Amount must be greater than 0", http.StatusBadRequest)
		return
	}
	if req.PaymentValidationUrl == "" {
		sendError(w, "Payment validation URL is required", http.StatusBadRequest)
		return
	}

	// Create invoice
	invoice, err := ic.invoiceManager.CreateInvoice(req.UserID, req.Month, req.Year, req.Amount, req.PaymentValidationUrl)
	if err != nil {
		if err.Error() == "invoice already exists" {
			sendError(w, err.Error(), http.StatusConflict)
			return
		}
		sendError(w, "Failed to create invoice: "+err.Error(), http.StatusInternalServerError)
		return
	}

	response := invoiceToResponse(invoice)
	sendData(w, response, http.StatusCreated)
}

// CheckPaymentAndUpdate checks payment status and updates invoice
// @Summary Check payment status
// @Description Checks the payment validation URL and updates invoice status if paid
// @Tags Invoice Management
// @Produce json
// @Param invoiceID path string true "Invoice ID"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} InvoiceResponse "Payment status checked and updated"
// @Failure 400 {object} ErrorResponse "Invalid invoice ID"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 404 {object} ErrorResponse "Invoice not found"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/{invoiceID}/check-payment [post]
func (ic *InvoiceController) CheckPaymentAndUpdate(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoiceID := chi.URLParam(r, "invoiceID")
	if invoiceID == "" {
		sendError(w, "Invoice ID is required", http.StatusBadRequest)
		return
	}

	invoice, err := ic.invoiceManager.CheckPaymentAndUpdate(invoiceID)
	if err != nil {
		if err.Error() == "failed to get invoice: invoice not found" {
			sendError(w, "Invoice not found", http.StatusNotFound)
			return
		}
		sendError(w, "Failed to check payment: "+err.Error(), http.StatusInternalServerError)
		return
	}

	response := invoiceToResponse(invoice)
	sendData(w, response, http.StatusOK)
}

// GetUserUnpaidInvoices returns all unpaid invoices for the authenticated user
// @Summary Get user's unpaid invoices
// @Description Returns all unpaid invoices for the authenticated user
// @Tags Invoice Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {array} InvoiceResponse "List of unpaid invoices"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/unpaid [get]
func (ic *InvoiceController) GetUserUnpaidInvoices(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoices, err := ic.invoiceManager.GetUserUnpaidInvoices(authUser.UserID)
	if err != nil {
		sendError(w, "Failed to get unpaid invoices: "+err.Error(), http.StatusInternalServerError)
		return
	}

	responses := invoicesToResponses(invoices)
	sendData(w, responses, http.StatusOK)
}

// GetUserInvoices returns all invoices for the authenticated user
// @Summary Get user's invoices
// @Description Returns all invoices for the authenticated user
// @Tags Invoice Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {array} InvoiceResponse "List of user invoices"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices [get]
func (ic *InvoiceController) GetUserInvoices(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoices, err := ic.invoiceManager.GetUserInvoices(authUser.UserID)
	if err != nil {
		sendError(w, "Failed to get invoices: "+err.Error(), http.StatusInternalServerError)
		return
	}

	responses := invoicesToResponses(invoices)
	sendData(w, responses, http.StatusOK)
}

// GetInvoiceByID returns a specific invoice by ID
// @Summary Get invoice by ID
// @Description Returns a specific invoice by ID (only accessible by invoice owner)
// @Tags Invoice Management
// @Produce json
// @Param invoiceID path string true "Invoice ID"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} InvoiceResponse "Invoice details"
// @Failure 400 {object} ErrorResponse "Invalid invoice ID"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 403 {object} ErrorResponse "Access denied"
// @Failure 404 {object} ErrorResponse "Invoice not found"
// @Router /api/v1/invoices/{invoiceID} [get]
func (ic *InvoiceController) GetInvoiceByID(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoiceID := chi.URLParam(r, "invoiceID")
	if invoiceID == "" {
		sendError(w, "Invoice ID is required", http.StatusBadRequest)
		return
	}

	invoice, err := ic.invoiceManager.GetInvoiceByID(invoiceID)
	if err != nil {
		sendError(w, "Invoice not found", http.StatusNotFound)
		return
	}

	// Ensure user can only access their own invoices
	if invoice.UserID != authUser.UserID {
		sendError(w, "Access denied: You can only access your own invoices", http.StatusForbidden)
		return
	}

	response := invoiceToResponse(invoice)
	sendData(w, response, http.StatusOK)
}

// GenerateMonthlyInvoice creates a monthly invoice for the authenticated user
// @Summary Generate monthly invoice
// @Description Creates a monthly invoice for the authenticated user
// @Tags Invoice Management
// @Accept json
// @Produce json
// @Param request body GenerateMonthlyInvoiceRequest true "Monthly invoice data"
// @Param Authorization header string true "Bearer token"
// @Success 201 {object} InvoiceResponse "Monthly invoice created successfully"
// @Failure 400 {object} ErrorResponse "Invalid request body"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 409 {object} ErrorResponse "Invoice already exists"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/generate [post]
func (ic *InvoiceController) GenerateMonthlyInvoice(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	var req GenerateMonthlyInvoiceRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Validate required fields
	if req.Month < 1 || req.Month > 12 {
		sendError(w, "Month must be between 1 and 12", http.StatusBadRequest)
		return
	}
	if req.Year < 2020 {
		sendError(w, "Year must be 2020 or later", http.StatusBadRequest)
		return
	}
	if req.Amount <= 0 {
		sendError(w, "Amount must be greater than 0", http.StatusBadRequest)
		return
	}
	if req.PaymentValidationUrl == "" {
		sendError(w, "Payment validation URL is required", http.StatusBadRequest)
		return
	}

	// Generate monthly invoice for authenticated user
	invoice, err := ic.invoiceManager.GenerateMonthlyInvoice(authUser.UserID, req.Month, req.Year, req.Amount, req.PaymentValidationUrl)
	if err != nil {
		if err.Error() == "invoice already exists" {
			sendError(w, err.Error(), http.StatusConflict)
			return
		}
		sendError(w, "Failed to generate monthly invoice: "+err.Error(), http.StatusInternalServerError)
		return
	}

	response := invoiceToResponse(invoice)
	sendData(w, response, http.StatusCreated)
}

// UpdateInvoice updates an existing invoice
// @Summary Update invoice
// @Description Updates an existing invoice (only accessible by invoice owner)
// @Tags Invoice Management
// @Accept json
// @Produce json
// @Param invoiceID path string true "Invoice ID"
// @Param request body UpdateInvoiceRequest true "Updated invoice data"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} InvoiceResponse "Invoice updated successfully"
// @Failure 400 {object} ErrorResponse "Invalid request"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 403 {object} ErrorResponse "Access denied"
// @Failure 404 {object} ErrorResponse "Invoice not found"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/{invoiceID} [put]
func (ic *InvoiceController) UpdateInvoice(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoiceID := chi.URLParam(r, "invoiceID")
	if invoiceID == "" {
		sendError(w, "Invoice ID is required", http.StatusBadRequest)
		return
	}

	var req UpdateInvoiceRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	// Get current invoice
	invoice, err := ic.invoiceManager.GetInvoiceByID(invoiceID)
	if err != nil {
		sendError(w, "Invoice not found", http.StatusNotFound)
		return
	}

	// Ensure user can only update their own invoices
	if invoice.UserID != authUser.UserID {
		sendError(w, "Access denied: You can only update your own invoices", http.StatusForbidden)
		return
	}

	// Update fields if provided
	if req.Amount != nil {
		if *req.Amount <= 0 {
			sendError(w, "Amount must be greater than 0", http.StatusBadRequest)
			return
		}
		invoice.Amount = *req.Amount
	}

	if req.PaymentValidationUrl != nil {
		if *req.PaymentValidationUrl == "" {
			sendError(w, "Payment validation URL cannot be empty", http.StatusBadRequest)
			return
		}
		invoice.PaymentValidationUrl = *req.PaymentValidationUrl
	}

	// Update invoice
	if err := ic.invoiceManager.UpdateInvoice(invoice); err != nil {
		sendError(w, "Failed to update invoice: "+err.Error(), http.StatusInternalServerError)
		return
	}

	response := invoiceToResponse(invoice)
	sendData(w, response, http.StatusOK)
}

// DeleteInvoice deletes an existing invoice
// @Summary Delete invoice
// @Description Deletes an existing invoice (only accessible by invoice owner)
// @Tags Invoice Management
// @Produce json
// @Param invoiceID path string true "Invoice ID"
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} SuccessResponse "Invoice deleted successfully"
// @Failure 400 {object} ErrorResponse "Invalid invoice ID"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 403 {object} ErrorResponse "Access denied"
// @Failure 404 {object} ErrorResponse "Invoice not found"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/{invoiceID} [delete]
func (ic *InvoiceController) DeleteInvoice(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoiceID := chi.URLParam(r, "invoiceID")
	if invoiceID == "" {
		sendError(w, "Invoice ID is required", http.StatusBadRequest)
		return
	}

	// Get invoice to check ownership
	invoice, err := ic.invoiceManager.GetInvoiceByID(invoiceID)
	if err != nil {
		sendError(w, "Invoice not found", http.StatusNotFound)
		return
	}

	// Ensure user can only delete their own invoices
	if invoice.UserID != authUser.UserID {
		sendError(w, "Access denied: You can only delete your own invoices", http.StatusForbidden)
		return
	}

	// Delete invoice
	if err := ic.invoiceManager.DeleteInvoice(invoiceID); err != nil {
		sendError(w, "Failed to delete invoice: "+err.Error(), http.StatusInternalServerError)
		return
	}

	sendSuccess(w, nil, "Invoice deleted successfully", http.StatusOK)
}

// GetInvoiceStatistics returns invoice statistics
// @Summary Get invoice statistics
// @Description Returns statistics about invoices (admin only)
// @Tags Invoice Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {object} map[string]interface{} "Invoice statistics"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/stats [get]
func (ic *InvoiceController) GetInvoiceStatistics(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	stats, err := ic.invoiceManager.GetInvoiceStatistics()
	if err != nil {
		sendError(w, "Failed to get statistics: "+err.Error(), http.StatusInternalServerError)
		return
	}

	sendData(w, stats, http.StatusOK)
}

// GetUserInvoicesByUserID returns all invoices for a specific user (admin endpoint)
// @Summary Get invoices by user ID
// @Description Returns all invoices for a specific user (admin only)
// @Tags Invoice Management
// @Produce json
// @Param userID path string true "User ID"
// @Param Authorization header string true "Bearer token"
// @Success 200 {array} InvoiceResponse "List of user invoices"
// @Failure 400 {object} ErrorResponse "Invalid user ID"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/user/{userID} [get]
func (ic *InvoiceController) GetUserInvoicesByUserID(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	userID := chi.URLParam(r, "userID")
	if userID == "" {
		sendError(w, "User ID is required", http.StatusBadRequest)
		return
	}

	invoices, err := ic.invoiceManager.GetUserInvoices(userID)
	if err != nil {
		sendError(w, "Failed to get invoices: "+err.Error(), http.StatusInternalServerError)
		return
	}

	responses := invoicesToResponses(invoices)
	sendData(w, responses, http.StatusOK)
}

// GetAllUnpaidInvoices returns all unpaid invoices in the system (admin endpoint)
// @Summary Get all unpaid invoices
// @Description Returns all unpaid invoices in the system (admin only)
// @Tags Invoice Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {array} InvoiceResponse "List of unpaid invoices"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/all/unpaid [get]
func (ic *InvoiceController) GetAllUnpaidInvoices(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoices, err := ic.invoiceManager.GetAllUnpaidInvoices()
	if err != nil {
		sendError(w, "Failed to get unpaid invoices: "+err.Error(), http.StatusInternalServerError)
		return
	}

	responses := invoicesToResponses(invoices)
	sendData(w, responses, http.StatusOK)
}

// GetAllPaidInvoices returns all paid invoices in the system (admin endpoint)
// @Summary Get all paid invoices
// @Description Returns all paid invoices in the system (admin only)
// @Tags Invoice Management
// @Produce json
// @Param Authorization header string true "Bearer token"
// @Success 200 {array} InvoiceResponse "List of paid invoices"
// @Failure 401 {object} ErrorResponse "Unauthorized"
// @Failure 500 {object} ErrorResponse "Internal server error"
// @Router /api/v1/invoices/all/paid [get]
func (ic *InvoiceController) GetAllPaidInvoices(w http.ResponseWriter, r *http.Request) {
	authUser := GetAuthenticatedUser(r)
	if authUser == nil {
		sendError(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	invoices, err := ic.invoiceManager.GetAllPaidInvoices()
	if err != nil {
		sendError(w, "Failed to get paid invoices: "+err.Error(), http.StatusInternalServerError)
		return
	}

	responses := invoicesToResponses(invoices)
	sendData(w, responses, http.StatusOK)
}
