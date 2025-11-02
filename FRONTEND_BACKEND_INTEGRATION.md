# Jarvis Frontend & Backend Integration Documentation

**Date:** November 2, 2025  
**Project:** Jarvis AI Agent Platform on Bitcoin L2 (Mezo)

---

## 📋 Table of Contents
1. [Executive Summary](#executive-summary)
2. [Frontend Overview](#frontend-overview)
3. [Backend Overview](#backend-overview)
4. [Integration Status](#integration-status)
5. [Missing Backend Features](#missing-backend-features)
6. [Critical Issues to Fix](#critical-issues-to-fix)
7. [Recommendations](#recommendations)
8. [API Endpoint Mapping](#api-endpoint-mapping)

---

## 🎯 Executive Summary

### Current Status
The Jarvis platform has a **fully functional frontend** built with Next.js 15, React, and TypeScript, featuring wallet authentication, dashboard interface, chat functionality, and billing management. The **backend API** (Go/Chi) is partially implemented with user management, container orchestration, and invoice handling.

### Key Gaps
- ❌ **Wallet authentication signature verification** needs testing
- ❌ **Container-to-agent message routing** not fully implemented
- ❌ **Bitcoin transaction verification** for subscription payments is missing
- ❌ **Invoice payment verification** endpoint needs blockchain integration
- ⚠️ **No chat history persistence** in database
- ⚠️ **Real-time agent status updates** not implemented

---

## 🎨 Frontend Overview

### Technology Stack
- **Framework:** Next.js 15 (App Router)
- **UI Library:** React 18 with TypeScript
- **Styling:** Tailwind CSS with custom design system
- **State Management:** React hooks + localStorage
- **Wallet Integration:** RainbowKit + Wagmi
- **HTTP Client:** Native Fetch API
- **Notifications:** Sonner (toast notifications)

### Page Structure

#### 1. Landing Page (`/app/page.tsx`)
**Purpose:** Marketing landing page with product information  
**Features:**
- Hero section with value proposition
- Problem/solution presentation
- Feature showcase (6 key features)
- Pricing information (4 tiers)
- "How It Works" flow (4 steps)
- Call-to-action buttons

**Key Elements:**
- Animated background with gradient orbs
- Suggested prompts for new users
- Wallet balance display
- Statistics cards (420M users, <2s transactions, 99.9% cost savings)

#### 2. Login Page (`/app/login/page.tsx`)
**Purpose:** Wallet-based authentication  
**Features:**
- RainbowKit wallet connection
- Ethereum signature request for verification
- Two-step authentication flow
- No password required (wallet-only auth)

**Authentication Flow:**
```
1. Connect wallet (MetaMask, WalletConnect, etc.)
2. Sign message to prove ownership
3. Backend verifies signature
4. JWT token issued (24h expiration)
5. Redirect to dashboard
```

**API Integration:**
```typescript
POST /api/v1/auth/wallet
Body: {
  wallet_address: string
  signature: string
  message: string
}
Response: {
  user_id: string
  username: string
  email: string
  container_id: string
  token: string
  created_at: string
  is_new_user: boolean
}
```

#### 3. Signup Page (`/app/signup/page.tsx`)
**Purpose:** New user registration with subscription payment  
**Features:**
- Wallet connection
- Optional profile details (name, email, password)
- **Bitcoin payment flow** (0.0003 BTC monthly subscription)
- Transaction ID verification
- Account creation after payment confirmation

**Payment Flow:**
```
1. Connect wallet
2. Display BTC payment address
3. User sends 0.0003 BTC
4. User enters transaction ID
5. Submit profile + tx_id to backend
6. Backend verifies payment (NOT YET IMPLEMENTED)
7. Create user account + container
```

**API Integration:**
```typescript
POST /api/v1/auth/wallet
Body: {
  wallet_address: string
  signature: string
  message: string
  full_name?: string
  email?: string
  password?: string
  btc_tx_id?: string  // Bitcoin transaction ID for subscription
}
```

#### 4. Dashboard (`/app/dashboard/page.tsx`)
**Purpose:** Main AI chat interface  
**Features:**
- Real-time chat with AI agent
- Voice input (Web Speech API)
- File attachments (up to multiple files)
- Message history display
- Cost estimation (0.01 MEZO per message)
- Loading states and error handling

**Chat Features:**
- **Text input** with Enter to send, Shift+Enter for new line
- **Voice input** with continuous recording and interim results
- **File attachments** (.txt, .pdf, .doc, .json, .js, .ts, .py, .sol, .md)
- **Suggested prompts** for new users (6 pre-built queries)
- **Real-time status** indicators (recording, sending, loading)

**API Integration:**
```typescript
POST /api/v1/containers/message
Headers: { Authorization: "Bearer <token>" }
Body: { message: string }
Response: {
  response: string
  processed_at: string
  user_id: string
  container_id: string
}
```

#### 5. Profile & Billing (`/app/dashboard/profile/page.tsx`)
**Purpose:** User profile management and invoice history  
**Features:**
- Two-tab interface (Profile & Billing)
- Profile editing (username, email)
- Account information display (user ID, container ID, timestamps)
- **Invoice management system**:
  - View all invoices (paid & unpaid)
  - Payment status badges
  - Invoice statistics dashboard
  - Payment verification button
  - Transaction history

**Invoice Features:**
- **Statistics Cards:**
  - Unpaid count + total amount
  - Paid count + total amount
  - Total invoices + grand total
  - Average invoice amount
- **Invoice List:**
  - Sorted by status (unpaid first)
  - Month/year display
  - Amount with currency
  - Payment date (if paid)
  - Payment URL/transaction hash
  - "Pay Now" action button
- **Mock Data Fallback:** If API fails, displays demo invoices

**API Integration:**
```typescript
// Get user profile
GET /api/v1/users/profile
Headers: { Authorization: "Bearer <token>" }

// Update profile
PUT /api/v1/users/{userID}
Body: { username?: string, email?: string }

// Get all invoices
GET /api/v1/invoices
Response: Invoice[]

// Get unpaid invoices
GET /api/v1/invoices/unpaid

// Verify payment
POST /api/v1/invoices/{invoiceID}/check-payment
```

### Shared Components

#### Dashboard Layout (`/app/dashboard/layout.tsx`)
**Features:**
- Collapsible sidebar with recent chats
- Top navigation bar with breadcrumbs
- Wallet balance display (MEZO tokens)
- User profile dropdown
- Authentication guard (redirects if not logged in)
- Profile loading on mount
- Logout functionality

**Navigation:**
- Dashboard → Chat (main)
- Dashboard → Profile
- Recent chats sidebar (4 most recent, currently mock data)
- "New Chat" button

### API Client (`/lib/api-client.ts`)
**Purpose:** Centralized API communication layer  
**Features:**
- Type-safe API calls
- Automatic token injection
- Error handling with typed responses
- Helper functions for auth state
- localStorage integration

**Exported Functions:**
- `apiClient.auth.*` - Authentication endpoints
- `apiClient.users.*` - User management
- `apiClient.containers.*` - Agent communication
- `apiClient.invoices.*` - Billing management
- `isAuthenticated()` - Check auth status
- `getCurrentUser()` - Get user from localStorage
- `getContainerInfo()` - Get container details

---

## 🔧 Backend Overview

### Technology Stack
- **Language:** Go 1.21+
- **Framework:** Chi (lightweight HTTP router)
- **Database:** PostgreSQL (with GORM-like patterns)
- **Container Orchestration:** Docker
- **Documentation:** Swagger/OpenAPI

### Architecture

```
api/
├── main.go                 # Server entry point, routing, middleware
├── database.go             # Database connection management
├── controllers/            # HTTP request handlers
│   ├── auth.go            # Wallet auth, JWT token management
│   ├── user_controller.go # User CRUD operations
│   ├── container_controller.go # Agent communication
│   ├── invoice.go         # Billing & invoices
│   └── common.go          # Shared response helpers
├── services/              # Business logic layer
│   ├── user_manager.go    # User operations
│   ├── container_manager.go # Docker container management
│   └── invoice_manager.go # Invoice operations
├── repository/            # Data access layer
│   ├── user_repository.go
│   ├── container_repository.go
│   └── invoice_repository.go
└── data/                  # Data models
    ├── user.go
    ├── container.go
    └── invoice.go
```

### Implemented Features

#### Authentication (`controllers/auth.go`)
✅ **Wallet Authentication**
- Ethereum signature verification (ECDSA recovery)
- User creation on first login
- JWT token generation (base64 encoded, 24h expiration)
- Auto-container provisioning for new users

✅ **Auth Middleware**
- Bearer token validation
- Token expiration checking
- User context injection
- Ownership verification

#### User Management (`controllers/user_controller.go`)
✅ **User Registration**
- Username, email, password validation
- Scrypt password hashing
- Duplicate email/username checking
- Automatic Docker container creation
- JWT token issuance

✅ **User Profile**
- Get authenticated user profile
- Update profile (username, email)
- Get user by ID (ownership enforced)
- Delete user account (with container cleanup)

✅ **User Login**
- Email + password authentication
- Password verification (scrypt)
- JWT token generation
- Last active timestamp update

#### Container Management (`controllers/container_controller.go`)
✅ **Message Sending**
- Send message to user's agent container
- Container availability check
- Response forwarding

✅ **Container Status**
- Get container health status
- Port information
- Running state check
- Creation/last used timestamps

✅ **Container Control**
- Start container
- Stop container
- Container ownership verification

#### Invoice Management (`controllers/invoice.go`)
✅ **Invoice CRUD**
- Create invoice (manual)
- Generate monthly invoice (automated)
- Get user invoices (all/unpaid)
- Update invoice amount/URL
- Delete invoice (ownership enforced)

✅ **Payment Verification**
- Check payment status endpoint
- Update invoice as paid
- Record payment timestamp

✅ **Admin Functions**
- Get invoice statistics
- Get all unpaid/paid invoices
- Get invoices by user ID

### Database Schema

#### Users Table
```sql
CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password VARCHAR(255),  -- hashed with scrypt
  wallet_address VARCHAR(42) UNIQUE,  -- Ethereum address
  container_id VARCHAR(64),
  created_at TIMESTAMP DEFAULT NOW(),
  last_active TIMESTAMP DEFAULT NOW()
);
```

#### Containers Table
```sql
CREATE TABLE containers (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(36) REFERENCES users(id),
  port INTEGER,
  status VARCHAR(20),
  created TIMESTAMP DEFAULT NOW(),
  last_used TIMESTAMP DEFAULT NOW(),
  is_running BOOLEAN DEFAULT FALSE
);
```

#### Invoices Table
```sql
CREATE TABLE invoices (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) REFERENCES users(id),
  month INTEGER CHECK (month >= 1 AND month <= 12),
  year INTEGER CHECK (year >= 2020),
  amount DECIMAL(10, 2),
  payment_validation_url VARCHAR(500),
  is_paid BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  last_active TIMESTAMP DEFAULT NOW(),
  paid_at TIMESTAMP
);
```

---

## ✅ Integration Status

### ✅ Working Integrations

1. **User Registration & Login** ✅
   - Traditional email/password works
   - Wallet authentication functional
   - Token generation/validation working
   - Container auto-provisioning on signup

2. **Profile Management** ✅
   - Get user profile
   - Update username/email
   - View account details
   - Logout functionality

3. **Invoice Display** ✅
   - Fetch all invoices
   - Fetch unpaid invoices
   - Display invoice history
   - Show payment status

### ⚠️ Partially Working

1. **Chat Functionality** ⚠️
   - Backend accepts messages
   - **Missing:** Actual agent response generation
   - **Issue:** `/containers/message` returns static response

2. **Payment Verification** ⚠️
   - Frontend sends transaction IDs
   - Backend has endpoint
   - **Missing:** Blockchain transaction verification
   - **Issue:** No actual Bitcoin payment checking

### ❌ Not Working / Missing

1. **Bitcoin Transaction Verification** ❌
   - Frontend collects BTC tx_id during signup
   - Backend accepts btc_tx_id parameter
   - **Missing:** Integration with Bitcoin/Mezo blockchain
   - **Missing:** Transaction amount verification
   - **Missing:** Payment confirmation before account activation

2. **Chat History Persistence** ❌
   - Frontend displays messages in UI only
   - **Missing:** Database table for chat messages
   - **Missing:** API endpoints to save/retrieve chat history
   - **Missing:** Message pagination/search

3. **Container Health Monitoring** ❌
   - Backend checks if container is running
   - **Missing:** Real-time status updates
   - **Missing:** Container restart on failure
   - **Missing:** Resource usage metrics

4. **File Upload Handling** ❌
   - Frontend has file attachment UI
   - **Missing:** Backend multipart/form-data handling
   - **Missing:** File storage (S3, local, etc.)
   - **Missing:** File processing in agent context

5. **Voice Input Processing** ❌
   - Frontend captures voice with Web Speech API
   - **Missing:** Audio file upload option
   - **Missing:** Server-side speech-to-text (if needed)

---

## 🚨 Missing Backend Features

### High Priority (Critical for Launch)

#### 1. Bitcoin Payment Verification
**Impact:** Users can sign up without actually paying  
**Location:** `api/controllers/auth.go` → `WalletAuth()`

**Current Code:**
```go
// Line ~200 in auth.go
btc_tx_id := req.BtcTxId  // Received but NOT verified
```

**What's Needed:**
```go
// Pseudo-code for payment verification
func VerifyBitcoinTransaction(txId string, expectedAmount float64, recipientAddress string) (bool, error) {
    // 1. Connect to Bitcoin node or blockchain API (e.g., BlockCypher, Blockchain.info)
    // 2. Fetch transaction details by txId
    // 3. Verify:
    //    - Transaction exists and is confirmed
    //    - Amount matches 0.0003 BTC (or configured subscription price)
    //    - Recipient address matches your wallet
    //    - Transaction is not already used (prevent double-spending)
    // 4. Return true if all checks pass
}
```

**Implementation Steps:**
1. Add Bitcoin RPC client or use blockchain API (BlockCypher, Blockcypher, etc.)
2. Create `VerifyMezoTransaction()` function
3. Store used transaction IDs to prevent reuse
4. Only create user account after successful verification
5. Handle pending transactions (0-6 confirmations)

**Example API:**
```bash
# BlockCypher API for Bitcoin
GET https://api.blockcypher.com/v1/btc/main/txs/{tx_hash}
```

#### 2. Agent Message Routing
**Impact:** Chat doesn't actually communicate with AI agent  
**Location:** `api/services/container_manager.go` → `SendMessage()`

**Current Code:**
```go
func (cm *ContainerManager) SendMessage(containerID string, message string) (string, error) {
    // TODO: Route message to actual agent running in Docker container
    return "Echo: " + message, nil  // Placeholder response
}
```

**What's Needed:**
```go
func (cm *ContainerManager) SendMessage(containerID string, message string) (string, error) {
    // 1. Get container IP and port
    containerInfo, err := cm.GetContainer(containerID)
    if err != nil {
        return "", err
    }
    
    // 2. Send HTTP request to agent's /chat endpoint
    // Example: http://172.17.0.2:5000/chat
    url := fmt.Sprintf("http://%s:%d/chat", containerInfo.IP, containerInfo.Port)
    
    body, _ := json.Marshal(map[string]string{"message": message})
    resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
    if err != nil {
        return "", fmt.Errorf("failed to reach agent: %w", err)
    }
    defer resp.Body.Close()
    
    // 3. Parse agent's response
    var result map[string]string
    json.NewDecoder(resp.Body).Decode(&result)
    
    return result["response"], nil
}
```

**Requirements:**
- Agent container must expose HTTP endpoint (e.g., Flask server on port 5000)
- Implement `/chat` endpoint in agent code
- Handle agent timeout/errors gracefully

#### 3. Chat History Database
**Impact:** Users lose chat history on page refresh  
**Location:** New table needed

**Database Schema:**
```sql
CREATE TABLE chat_messages (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) REFERENCES users(id),
  container_id VARCHAR(64),
  role VARCHAR(10) CHECK (role IN ('user', 'agent', 'system')),
  content TEXT NOT NULL,
  metadata JSONB,  -- For storing file attachments, tokens, etc.
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX (user_id, created_at)
);
```

**New API Endpoints:**
```go
// POST /api/v1/chat/messages - Save message
// GET /api/v1/chat/messages?limit=50&offset=0 - Get history
// GET /api/v1/chat/conversations - Get conversation list
// DELETE /api/v1/chat/conversations/{id} - Delete conversation
```

**Controller Implementation:**
```go
// api/controllers/chat_controller.go
type ChatController struct {
    chatManager *services.ChatManager
}

func (cc *ChatController) SaveMessage(w http.ResponseWriter, r *http.Request) {
    // Save user message to database
    // Save agent response to database
}

func (cc *ChatController) GetChatHistory(w http.ResponseWriter, r *http.Request) {
    // Fetch messages for authenticated user
    // Support pagination
}
```

### Medium Priority (Post-Launch)

#### 4. File Upload & Storage
**What's Needed:**
- Multipart form-data handling in Go
- File storage system (AWS S3, MinIO, or local filesystem)
- File type validation
- Virus scanning
- File size limits
- File context injection into agent prompts

**Implementation:**
```go
// POST /api/v1/files/upload
func (fc *FileController) UploadFile(w http.ResponseWriter, r *http.Request) {
    r.ParseMultipartForm(10 << 20) // 10 MB limit
    
    file, handler, err := r.FormFile("file")
    if err != nil {
        sendError(w, "Failed to upload file", http.StatusBadRequest)
        return
    }
    defer file.Close()
    
    // Save to S3 or local storage
    fileID := uuid.New().String()
    fileURL := saveToS3(fileID, file, handler.Filename)
    
    // Save metadata to database
    fileRecord := &data.File{
        ID: fileID,
        UserID: authUser.UserID,
        Filename: handler.Filename,
        URL: fileURL,
        Size: handler.Size,
    }
    
    sendData(w, fileRecord, http.StatusCreated)
}
```

#### 5. Invoice Auto-Generation Cron Job
**What's Needed:**
- Monthly cron job to generate invoices
- Usage tracking (API calls, compute time)
- Dynamic pricing based on usage
- Email notifications for unpaid invoices

**Implementation:**
```go
// services/billing_service.go
func (bs *BillingService) GenerateMonthlyInvoices() {
    // Run on 1st of each month
    users, _ := bs.userManager.GetAllUsers()
    
    for _, user := range users {
        usage := bs.calculateUsage(user.ID)
        amount := bs.calculateAmount(usage)
        
        invoice := &data.Invoice{
            UserID: user.ID,
            Month: time.Now().Month(),
            Year: time.Now().Year(),
            Amount: amount,
        }
        
        bs.invoiceManager.CreateInvoice(invoice)
        bs.emailService.SendInvoiceEmail(user.Email, invoice)
    }
}
```

#### 6. Container Resource Limits
**What's Needed:**
- Docker memory/CPU limits
- Container auto-restart policies
- Resource usage monitoring
- Container cleanup for inactive users

**Docker Compose Example:**
```yaml
services:
  user-agent:
    image: jarvis-agent:latest
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    restart: on-failure
```

#### 7. Real-Time WebSocket Updates
**What's Needed:**
- WebSocket connection for live agent responses
- Typing indicators
- Container status updates
- Usage metrics streaming

**Implementation:**
```go
// api/controllers/websocket_controller.go
import "github.com/gorilla/websocket"

var upgrader = websocket.Upgrader{
    ReadBufferSize:  1024,
    WriteBufferSize: 1024,
}

func (wc *WebSocketController) HandleConnection(w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        return
    }
    defer conn.Close()
    
    // Handle messages
    for {
        messageType, p, err := conn.ReadMessage()
        if err != nil {
            return
        }
        
        // Process message and send response
        response := wc.processMessage(p)
        conn.WriteMessage(messageType, response)
    }
}
```

### Low Priority (Future Enhancements)

#### 8. Admin Dashboard
- View all users
- Monitor container health
- Invoice management
- System metrics

#### 9. Rate Limiting
- Per-user API rate limits
- DDoS protection
- Token bucket algorithm

#### 10. Analytics & Logging
- Request logging
- Error tracking (Sentry)
- Usage analytics
- Performance monitoring

---

## 🔴 Critical Issues to Fix

### 1. Security Vulnerabilities

#### Issue: JWT Token Security
**Location:** `api/controllers/auth.go`  
**Problem:** Tokens are simple base64-encoded JSON, not cryptographically signed

**Current Implementation:**
```go
func EncodeToken(userID string, expirationHours int) (string, error) {
    claims := TokenClaims{
        UserID:    userID,
        ExpiresAt: time.Now().Add(time.Duration(expirationHours) * time.Hour),
    }
    claimsBytes, _ := json.Marshal(claims)
    token := base64.URLEncoding.EncodeToString(claimsBytes)  // ❌ NOT SECURE
    return token, nil
}
```

**Solution:** Use proper JWT library
```go
import "github.com/golang-jwt/jwt/v5"

var jwtSecret = []byte(os.Getenv("JWT_SECRET")) // Load from environment

func EncodeToken(userID string, expirationHours int) (string, error) {
    claims := jwt.MapClaims{
        "user_id": userID,
        "exp":     time.Now().Add(time.Duration(expirationHours) * time.Hour).Unix(),
    }
    
    token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
    return token.SignedString(jwtSecret)
}

func DecodeToken(tokenString string) (*TokenClaims, error) {
    token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
        return jwtSecret, nil
    })
    
    if claims, ok := token.Claims.(jwt.MapClaims); ok && token.Valid {
        return &TokenClaims{
            UserID:    claims["user_id"].(string),
            ExpiresAt: time.Unix(int64(claims["exp"].(float64)), 0),
        }, nil
    }
    
    return nil, err
}
```

#### Issue: Password Storage
**Status:** ✅ GOOD - Using scrypt  
**Note:** Current implementation is secure

#### Issue: SQL Injection
**Status:** ⚠️ Needs Review  
**Action:** Ensure all database queries use parameterized statements

### 2. Error Handling

#### Issue: Generic Error Messages
**Location:** Multiple controllers  
**Problem:** Exposing internal errors to frontend

**Bad Example:**
```go
sendError(w, "Failed to create user: "+err.Error(), http.StatusInternalServerError)
```

**Better Approach:**
```go
log.Printf("Failed to create user: %v", err) // Log internally
sendError(w, "Failed to create user account. Please try again.", http.StatusInternalServerError)
```

### 3. CORS Configuration

#### Issue: Open CORS Policy
**Location:** `api/main.go` line ~30  
**Problem:** Allows all origins

**Current:**
```go
w.Header().Set("Access-Control-Allow-Origin", "*")  // ❌ TOO PERMISSIVE
```

**Better:**
```go
allowedOrigins := os.Getenv("ALLOWED_ORIGINS") // e.g., "https://jarvis.example.com"
w.Header().Set("Access-Control-Allow-Origin", allowedOrigins)
w.Header().Set("Access-Control-Allow-Credentials", "true")
```

### 4. Database Connection Pooling

#### Issue: No Connection Pool Configuration
**Location:** `api/database.go`  
**Action:** Configure max connections, idle timeout

```go
db.SetMaxOpenConns(25)
db.SetMaxIdleConns(5)
db.SetConnMaxLifetime(5 * time.Minute)
```

---

## 💡 Recommendations

### Immediate Actions (Before Launch)

1. **Implement Bitcoin Payment Verification** ⚡
   - Integrate with Mezo blockchain or Bitcoin node
   - Verify transaction amount and recipient
   - Store used transaction IDs
   - **ETA:** 2-3 days

2. **Fix JWT Token Security** ⚡
   - Replace base64 encoding with proper JWT
   - Use environment variable for secret key
   - Implement token refresh mechanism
   - **ETA:** 4-6 hours

3. **Implement Agent Message Routing** ⚡
   - Connect backend to Docker agent containers
   - Test agent HTTP endpoint
   - Handle timeout and errors
   - **ETA:** 1-2 days

4. **Add Chat History Persistence** 🔄
   - Create database table
   - Implement save/retrieve endpoints
   - Update frontend to load history
   - **ETA:** 2-3 days

5. **Test End-to-End Flow** ✅
   - Signup → Payment → Login → Chat → Billing
   - Test with real Bitcoin testnet transactions
   - Verify all error cases
   - **ETA:** 1 day

### Post-Launch Improvements

1. **Add WebSocket Support** (Week 2-3)
   - Real-time chat updates
   - Typing indicators
   - Live agent status

2. **Implement File Uploads** (Week 3-4)
   - Storage system (S3/MinIO)
   - File context in agent prompts
   - File management UI

3. **Build Admin Dashboard** (Week 4-6)
   - User management
   - Invoice oversight
   - System monitoring

4. **Add Usage Analytics** (Week 6-8)
   - Track API calls
   - Monitor costs
   - Generate usage reports

5. **Implement Rate Limiting** (Week 8+)
   - Prevent abuse
   - Fair usage policies
   - Tiered access levels

### Infrastructure Recommendations

1. **Environment Variables**
   ```bash
   # .env.production
   DATABASE_URL=postgresql://user:pass@localhost:5432/jarvis
   JWT_SECRET=<random-256-bit-secret>
   BITCOIN_NODE_URL=https://btc-node.example.com
   BITCOIN_WALLET_ADDRESS=bc1q...
   ALLOWED_ORIGINS=https://jarvis.dogukangun.com
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=noreply@jarvis.com
   SMTP_PASSWORD=<password>
   ```

2. **Docker Setup**
   - Use docker-compose for development
   - Kubernetes for production scaling
   - Container orchestration with health checks
   - Automated container cleanup

3. **Monitoring & Logging**
   - Set up Prometheus + Grafana for metrics
   - Use Sentry for error tracking
   - Implement structured logging (JSON format)
   - Set up alerts for critical errors

4. **CI/CD Pipeline**
   - GitHub Actions for automated testing
   - Automated deployment to staging
   - Manual approval for production
   - Rollback mechanism

---

## 📚 API Endpoint Mapping

### Authentication

| Endpoint | Method | Frontend Usage | Backend Status | Notes |
|----------|--------|----------------|----------------|-------|
| `/api/v1/auth/wallet` | POST | Login, Signup | ✅ Implemented | Needs BTC verification |
| `/api/v1/auth/logout` | POST | Logout | ✅ Implemented | Client-side token removal |

### User Management

| Endpoint | Method | Frontend Usage | Backend Status | Notes |
|----------|--------|----------------|----------------|-------|
| `/api/v1/users/register` | POST | Not used | ✅ Implemented | Deprecated in favor of wallet auth |
| `/api/v1/users/login` | POST | Not used | ✅ Implemented | Deprecated in favor of wallet auth |
| `/api/v1/users/profile` | GET | Dashboard, Profile | ✅ Implemented | Returns full user data |
| `/api/v1/users/{userID}` | GET | Not used | ✅ Implemented | Ownership enforced |
| `/api/v1/users/{userID}` | PUT | Profile page | ✅ Implemented | Update username/email |
| `/api/v1/users/{userID}` | DELETE | Not used | ✅ Implemented | Deletes user + container |

### Container/Agent

| Endpoint | Method | Frontend Usage | Backend Status | Notes |
|----------|--------|----------------|----------------|-------|
| `/api/v1/containers/message` | POST | Dashboard chat | ⚠️ Placeholder | Returns echo response |
| `/api/v1/containers/status` | GET | Not used | ✅ Implemented | Container health check |
| `/api/v1/containers/start` | POST | Not used | ✅ Implemented | Manual container start |
| `/api/v1/containers/stop` | POST | Not used | ✅ Implemented | Manual container stop |
| `/api/v1/containers/{id}` | GET | Not used | ✅ Implemented | Get container details |

### Invoices

| Endpoint | Method | Frontend Usage | Backend Status | Notes |
|----------|--------|----------------|----------------|-------|
| `/api/v1/invoices` | GET | Profile billing tab | ✅ Implemented | Returns user invoices |
| `/api/v1/invoices` | POST | Not used | ✅ Implemented | Manual invoice creation |
| `/api/v1/invoices/unpaid` | GET | Profile billing tab | ✅ Implemented | Unpaid invoices only |
| `/api/v1/invoices/{id}` | GET | Not used | ✅ Implemented | Single invoice details |
| `/api/v1/invoices/{id}` | PUT | Not used | ✅ Implemented | Update invoice amount/URL |
| `/api/v1/invoices/{id}` | DELETE | Not used | ✅ Implemented | Delete invoice |
| `/api/v1/invoices/{id}/check-payment` | POST | Profile "Pay Now" | ⚠️ No verification | Needs blockchain integration |
| `/api/v1/invoices/generate` | POST | Not used | ✅ Implemented | Create monthly invoice |
| `/api/v1/invoices/stats` | GET | Not used | ✅ Implemented | Admin statistics |

### Missing Endpoints (Needed)

| Endpoint | Purpose | Priority |
|----------|---------|----------|
| `/api/v1/chat/messages` | Save chat messages | High |
| `/api/v1/chat/history` | Retrieve chat history | High |
| `/api/v1/chat/conversations` | List all conversations | Medium |
| `/api/v1/files/upload` | Upload file attachments | Medium |
| `/api/v1/files/{id}` | Get uploaded file | Medium |
| `/api/v1/admin/users` | Admin user list | Low |
| `/api/v1/admin/containers` | Admin container overview | Low |

---

## 🎬 Conclusion

The Jarvis platform has a **solid foundation** with a polished frontend and functional backend core. The main gaps are:

1. **Payment verification** - Critical for monetization
2. **Agent communication** - Critical for core functionality
3. **Chat persistence** - Important for user experience
4. **Security hardening** - Critical for production

**Estimated Time to Production-Ready:**
- **With BTC verification:** 5-7 days
- **Without BTC verification (demo mode):** 2-3 days

**Next Steps:**
1. Prioritize Bitcoin payment verification
2. Fix JWT token security
3. Implement agent message routing
4. Add chat history database
5. Conduct comprehensive testing
6. Deploy to production

---

**Document Version:** 1.0  
**Last Updated:** November 2, 2025  
**Maintainer:** Jarvis Development Team
