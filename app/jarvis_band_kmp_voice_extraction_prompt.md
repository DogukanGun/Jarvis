
# Prompt for AI Agent: Implementation Plan (KMP + Android Voice Extraction)

You are a senior **Kotlin Multiplatform + Android audio/ML engineer**. Create a detailed implementation plan (milestones + tasks + file/module structure) for an app that performs **on-device voice extraction** on Android and is structured as a **Kotlin Multiplatform (KMP)** codebase to later support iOS.

## 0) Context / Product Goal

We are building a project called **Jarvis Band**. For now, the wearable device is not built yet. To demonstrate practicality, the **phone is the “device”** in V1.

The Android app will:

1. **Enroll** the user’s voice (create a voice profile/embedding)
2. In **live mode**, record mic audio, detect speech (VAD), and classify each speech segment as:
   - **User voice**
   - **Other voice**
3. Output only the **user voice segments** as:
   - raw PCM buffers and/or
   - timestamps and optionally saved WAV files
4. Later, these user-only segments will be sent to backend ASR/LLM, but for V1 this is optional. The focus is **voice extraction on-device**.

We will use **Kotlin Multiplatform** so that:

- audio capture + TFLite interpreter are Android-specific (androidMain)
- pipeline logic + state machine + thresholds + segmentation live in shared code (commonMain)

## 1) What “Voice Extraction” Means in V1

We are NOT doing perfect source separation like “remove all other speakers from the waveform” (that’s hard on mobile).
Instead, we do **segment-level extraction**:

- The mic stream is chunked into frames.
- VAD determines “speech vs silence” on small frames (10–30 ms).
- Contiguous speech frames become a **SpeechSegment**.
- For each SpeechSegment, compute a **speaker embedding** and compare against the enrolled profile:
  - If similarity > threshold → segment = USER → keep it
  - Else → segment = OTHER → drop or mark
- We “extract” the user by keeping **only segments classified as USER**.

This is enough for a strong product demo:

- “Only my voice triggers commands”
- “Other people talking near me are ignored”

## 2) Target Audio Format

Standardize everything early:

- **Sample rate:** 16 kHz
- **Channels:** mono
- **Encoding:** PCM 16-bit for capture, convert to Float [-1..1] for ML input
- Frame sizes: 10/20/30 ms frames (e.g. 160/320/480 samples @16k)

Android capture:

- Use `AudioRecord` with `ENCODING_PCM_16BIT`, mono, 16k
- Use a chunk size like 20ms or 40ms blocks and feed into pipeline

## 3) KMP Module Structure (Proposed)

Create these modules (agent can adjust naming but keep separation):

- `:app-android`  
  - UI (Compose), Android permissions, AudioRecord, Android-specific glue
- `:shared` (KMP root shared module)
  - `commonMain`:
    - domain interfaces, pipeline orchestration, segmentation, similarity, persistence abstraction
  - `androidMain`:
    - concrete implementations:
      - `AndroidAudioRecorder`
      - `TFLiteSpeakerEmbeddingModel`
      - `AndroidStorage` (encrypted storage)
      - `WebRtcVadAndroid` (if VAD library is JVM/Android)

Optional extra split if needed:

- `:shared:core-vad`
- `:shared:core-speaker`
- `:shared:core-pipeline`

But if that’s too much overhead, keep them as packages in `:shared`.

## 4) Key Components & Interfaces

Design these in `commonMain` so iOS can reuse later.

### 4.1 Voice Profile (Enrollment Output)

A `VoiceProfile` contains:

- `embedding: FloatArray`
- metadata: sample rate used, createdAt, model name/version, threshold used, etc.

### 4.2 Enrollment Use Case

User records 3–5 short voice samples (3–5 seconds each).

Enrollment pipeline:

- run VAD → keep only speech
- split into windows (e.g. 1 sec windows with overlap)
- compute embeddings per window
- average embeddings to create final profile
- store profile locally

Interfaces:

```kotlin
interface VoiceEnrollmentRepository {
  suspend fun addSample(pcm16: ShortArray)
  suspend fun finalize(): VoiceProfile
  suspend fun load(): VoiceProfile?
  suspend fun clear()
}
```

### 4.3 Live Extraction Pipeline

Streaming pipeline:

- input = mic PCM blocks
- output events = user speech segments, other speech segments, debug

```kotlin
interface VoiceExtractionPipeline {
  suspend fun start(profile: VoiceProfile)
  suspend fun process(pcm16: ShortArray) // streaming input
  suspend fun stop()
  val events: Flow<VoiceEvent>
}

sealed class VoiceEvent {
  data class UserSegment(val segment: VoiceSegment): VoiceEvent()
  data class OtherSegment(val segment: VoiceSegment): VoiceEvent()
  data class Level(val rmsDb: Float): VoiceEvent()
  data class State(val state: PipelineState): VoiceEvent()
}

data class VoiceSegment(
  val startMs: Long,
  val endMs: Long,
  val pcm16: ShortArray, // optional - if we keep audio
  val confidence: Float  // similarity score
)
```

### 4.4 VAD

Create interface:

```kotlin
interface VoiceActivityDetector {
  fun isSpeech(framePcm16: ShortArray): Boolean
}
```

Implementation options:

- Use WebRTC VAD library (Java/Kotlin wrapper) on Android
- If no immediate lib, implement a placeholder energy-based VAD for V1 but keep same interface and TODO.

### 4.5 Speaker Embedding Model

Interface:

```kotlin
interface SpeakerEmbeddingModel {
  suspend fun embedding(pcmFloat: FloatArray, sampleRate: Int = 16000): FloatArray
}
```

Android implementation uses TensorFlow Lite:

- model shipped in `assets/models/`
- preprocess: normalize, pad/trim to required input length
- output embedding dimension e.g. 192/256/512

Comparator:

```kotlin
interface SpeakerComparator {
  fun cosineSimilarity(a: FloatArray, b: FloatArray): Float
}
```

Add `VoiceConfig`:

- VAD aggressiveness
- minSpeechMs
- maxSegmentMs
- similarityThreshold (tunable)
- enrollmentSamplesCount

## 5) Android App UX Design (Two Screens)

Implement the app UI with Compose (simple but functional).

### Screen A: Enrollment

Elements:

- “Record sample” button (3–5 times)
- Progress indicator (Sample 1/5, 2/5…)
- Display mic level
- After enough samples: “Finalize Enrollment”
- After finalize: show “Enrollment complete” + allow “Re-enroll”

Flow:

1. Tap “Record Sample”
2. Record 3–5 sec audio
3. Run `addSample()`
4. Repeat
5. Tap finalize → profile stored

### Screen B: Live Extraction

Elements:

- Start/Stop listening
- Show current state: Listening / Speech / Processing / Idle
- Show live RMS bar
- Log list:
  - “USER speech 00:12–00:14 score 0.86”
  - “OTHER speech 00:15–00:17 score 0.42”
- Optional toggles:
  - “Save user segments as WAV”
  - “Auto-send user segments to backend” (optional)

## 6) Recording & Permissions

Android:

- request microphone permission
- handle foreground recording constraints
- implement a foreground service if needed for stable recording (optional for V1)

Audio capture:

- `AudioRecord` in coroutine
- push chunks to pipeline `process()`

## 7) Output / Debugging Features (Very Helpful)

Include developer toggles:

- Save raw mic to WAV for debugging
- Save user-only segments to WAV
- Show similarity threshold slider (debug)
- Show VAD aggressiveness selection
- Export logs for testing in noisy environments

## 8) Milestones (Plan Must Include)

Ask the agent to produce a plan with milestones such as:

**M1: Project skeleton**

- KMP setup, modules, dependencies, basic Compose UI

**M2: Audio capture**

- AudioRecord working, waveform/level UI

**M3: VAD integration**

- VAD interface + implementation (WebRTC or energy fallback)
- segmentation logic (silence gap -> end segment)

**M4: Enrollment**

- record samples, compute embeddings (even stub), store profile

**M5: Live classification**

- compute embedding on each speech segment
- similarity scoring + threshold
- emit events and show logs in UI

**M6: Save user segments**

- WAV writing utility
- store segments in app files

**M7: Performance & power**

- buffering, avoiding allocations, background thread usage
- minimal latency design

**M8: Optional backend integration**

- send user segments to server via WebSocket/HTTP

## 9) Constraints & Quality Requirements

- Keep code readable and documented (English is not the user’s first language)
- Use coroutines + Flow for streaming
- Avoid Android APIs in shared code
- Make configuration adjustable (threshold tuning is essential)
- Prefer incremental working state: even if ML model isn’t available yet, stub it with deterministic embeddings so pipeline can be tested

## 10) Deliverables Requested From You (The Agent)

1. A detailed implementation plan with steps, dependencies, and estimated complexity per step.
2. Proposed file/package structure.
3. Key classes + interfaces list.
4. Risks + mitigation:
   - Bluetooth / background restrictions
   - VAD accuracy
   - speaker model availability
   - latency and memory churn
5. A “V1 demo checklist” to ensure it looks impressive in a live demo.

---

If it helps, the final V1 demo story is:

- User enrolls their voice in 1 minute.
- In a noisy room, app listens.
- When user speaks → it logs USER and saves segment.
- When others speak → logs OTHER and ignores.
- Optional: send user segments to server → get ASR → Jarvis responds.

---

That’s the full scope. Produce the plan now.
