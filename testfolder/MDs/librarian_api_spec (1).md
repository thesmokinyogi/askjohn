# Contextual Librarian: API Specification

## Overview

RESTful API for interacting with the Contextual Librarian system. All endpoints return JSON unless otherwise specified.

---

## Base Configuration

```
Base URL: /api/v1
Content-Type: application/json
Authentication: Bearer token (JWT)
```

---

## 1. Corpus Management

### 1.1 Ingest Content

```http
POST /corpus/ingest
```

**Request Body:**
```json
{
  "content_type": "audio|text|document",
  "source": "file|url|text",
  "data": "base64_encoded_content | url | raw_text",
  "metadata": {
    "title": "string",
    "date": "ISO 8601 timestamp",
    "project": "string",
    "tags": ["string"],
    "format": "mp3|wav|txt|md|pdf",
    "context": "string (optional description)"
  }
}
```

**Response:**
```json
{
  "document_id": "uuid",
  "status": "processing|completed|failed",
  "chunks_created": 0,
  "embeddings_generated": 0,
  "processing_time_ms": 0,
  "extracted_concepts": ["string"],
  "detected_cross_references": ["document_id"]
}
```

### 1.2 Get Document

```http
GET /corpus/documents/{document_id}
```

**Response:**
```json
{
  "document_id": "uuid",
  "title": "string",
  "content": "string",
  "metadata": {
    "date": "ISO 8601",
    "project": "string",
    "tags": ["string"],
    "format": "string"
  },
  "chunks": [
    {
      "chunk_id": "uuid",
      "level": "document|section|paragraph",
      "content": "string",
      "position": 0
    }
  ],
  "related_documents": ["document_id"],
  "extracted_concepts": ["string"]
}
```

### 1.3 Search Corpus

```http
POST /corpus/search
```

**Request Body:**
```json
{
  "query": "string",
  "filters": {
    "date_range": {
      "start": "ISO 8601",
      "end": "ISO 8601"
    },
    "projects": ["string"],
    "tags": ["string"],
    "content_types": ["audio|text|document"]
  },
  "retrieval_strategy": {
    "levels": ["document", "section", "paragraph"],
    "max_results": 10,
    "include_cross_references": true,
    "temporal_preference": "earliest|latest|balanced"
  },
  "context": {
    "session_id": "uuid (optional)",
    "current_focus": "string (optional)"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "title": "string",
      "content": "string",
      "level": "document|section|paragraph",
      "relevance_score": 0.95,
      "metadata": {
        "date": "ISO 8601",
        "project": "string",
        "tags": ["string"]
      },
      "contextual_framing": "string (how this fits in intellectual landscape)",
      "cross_references": ["document_id"],
      "temporal_context": "string (early vs. evolved thinking)"
    }
  ],
  "total_results": 0,
  "search_time_ms": 0,
  "suggested_refinements": ["string"]
}
```

### 1.4 Delete Document

```http
DELETE /corpus/documents/{document_id}
```

**Response:**
```json
{
  "status": "deleted",
  "document_id": "uuid",
  "chunks_removed": 0,
  "graph_nodes_removed": 0
}
```

---

## 2. Librarian Intelligence

### 2.1 Query Librarian

```http
POST /librarian/query
```

**Request Body:**
```json
{
  "query": "string",
  "session_id": "uuid (creates new if not provided)",
  "options": {
    "include_retrieval": true,
    "max_sources": 5,
    "synthesis_depth": "quick|standard|deep",
    "show_reasoning": false
  }
}
```

**Response:**
```json
{
  "response": "string (synthesized answer)",
  "session_id": "uuid",
  "sources": [
    {
      "document_id": "uuid",
      "title": "string",
      "excerpt": "string",
      "relevance": "string (why this was retrieved)",
      "contextual_note": "string (how it fits)"
    }
  ],
  "reasoning_trace": {
    "reconstructed_context": "string",
    "retrieval_strategy": "string",
    "synthesis_approach": "string"
  },
  "emerging_patterns": ["string"],
  "suggested_followups": ["string"],
  "cross_references_surfaced": ["document_id"]
}
```

### 2.2 Get Intellectual Map

```http
GET /librarian/intellectual-map
```

**Response:**
```json
{
  "version": "timestamp",
  "core_themes": [
    {
      "theme": "string",
      "importance": 0.85,
      "related_themes": ["string"],
      "evolution": "string (how it's developed)"
    }
  ],
  "conceptual_graph": {
    "nodes": [
      {
        "concept": "string",
        "centrality": 0.75,
        "first_appearance": "document_id",
        "latest_articulation": "document_id"
      }
    ],
    "edges": [
      {
        "from": "concept",
        "to": "concept",
        "relationship": "string",
        "strength": 0.8
      }
    ]
  },
  "recurring_questions": ["string"],
  "terminology": {
    "term": "user-specific meaning"
  },
  "communication_patterns": {
    "preferred_depth": "concise|detailed|comprehensive",
    "reasoning_style": "first_principles|analogy|case_based",
    "presentation_preference": "direct|exploratory"
  }
}
```

### 2.3 Update Intellectual Map

```http
PATCH /librarian/intellectual-map
```

**Request Body:**
```json
{
  "updates": {
    "new_themes": ["string"],
    "theme_importance_changes": {
      "theme": 0.9
    },
    "new_connections": [
      {
        "concept_a": "string",
        "concept_b": "string",
        "relationship": "string"
      }
    ],
    "terminology_updates": {
      "term": "updated meaning"
    },
    "evolution_notes": ["string"]
  },
  "source": "user_correction|automated_analysis|conversation"
}
```

**Response:**
```json
{
  "status": "updated",
  "version": "new_timestamp",
  "changes_applied": 0,
  "validation_warnings": ["string"]
}
```

### 2.4 Get Cross-Corpus Understanding

```http
GET /librarian/cross-corpus-understanding
```

**Response:**
```json
{
  "version": "timestamp",
  "domain": "string",
  "shared_vocabulary": {
    "term": "meaning_in_corpus"
  },
  "concept_relationships": [
    {
      "concept_a": "string",
      "concept_b": "string",
      "relationship_type": "causes|enables|contrasts|extends",
      "strength": 0.85,
      "evidence": ["document_id"]
    }
  ],
  "open_questions": [
    {
      "question": "string",
      "context": "string",
      "related_documents": ["document_id"]
    }
  ],
  "decisions_made": [
    {
      "question": "string",
      "answer": "string",
      "reasoning": "string",
      "source": "document_id"
    }
  ],
  "idea_genealogy": [
    {
      "concept": "string",
      "evolution_chain": [
        {
          "document_id": "uuid",
          "date": "ISO 8601",
          "articulation": "string",
          "stage": "initial|developing|mature"
        }
      ]
    }
  ],
  "contradictions": [
    {
      "topic": "string",
      "position_a": "string",
      "position_b": "string",
      "source_a": "document_id",
      "source_b": "document_id",
      "temporal_gap": "duration"
    }
  ],
  "strongest_articulations": {
    "concept": {
      "document_id": "uuid",
      "excerpt": "string",
      "reason": "string"
    }
  }
}
```

---

## 3. Session Management

### 3.1 Create Session

```http
POST /sessions
```

**Request Body:**
```json
{
  "context": {
    "focus": "string (optional)",
    "project": "string (optional)",
    "goal": "string (optional)"
  }
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "created_at": "ISO 8601",
  "reconstructed_state": {
    "intellectual_map_version": "timestamp",
    "cross_corpus_version": "timestamp",
    "initial_context": "string"
  }
}
```

### 3.2 Get Session

```http
GET /sessions/{session_id}
```

**Response:**
```json
{
  "session_id": "uuid",
  "created_at": "ISO 8601",
  "last_activity": "ISO 8601",
  "conversation_state": {
    "current_focus": "string",
    "active_questions": ["string"],
    "recent_retrievals": [
      {
        "document_id": "uuid",
        "reason": "string",
        "timestamp": "ISO 8601"
      }
    ],
    "emerging_patterns": ["string"],
    "current_framing": "string"
  },
  "message_count": 0,
  "documents_accessed": ["uuid"]
}
```

### 3.3 Update Session State

```http
PATCH /sessions/{session_id}
```

**Request Body:**
```json
{
  "state_updates": {
    "current_focus": "string",
    "add_active_questions": ["string"],
    "remove_active_questions": ["string"],
    "emerging_patterns": ["string"],
    "current_framing": "string"
  }
}
```

**Response:**
```json
{
  "status": "updated",
  "session_id": "uuid",
  "updated_at": "ISO 8601"
}
```

### 3.4 Resume Session

```http
POST /sessions/{session_id}/resume
```

**Response:**
```json
{
  "session_id": "uuid",
  "context_summary": "string (what we were working on)",
  "suggested_continuation": "string",
  "recent_corpus_developments": [
    {
      "development": "string",
      "relevant_documents": ["uuid"],
      "relevance_to_session": "string"
    }
  ]
}
```

### 3.5 End Session

```http
POST /sessions/{session_id}/end
```

**Request Body:**
```json
{
  "save_insights": true,
  "summary": "string (optional user summary)"
}
```

**Response:**
```json
{
  "status": "ended",
  "session_id": "uuid",
  "duration_minutes": 0,
  "insights_captured": ["string"],
  "state_updates_applied": 0
}
```

---

## 4. Proactive Features

### 4.1 Detect Gaps

```http
POST /proactive/detect-gaps
```

**Request Body:**
```json
{
  "analysis_scope": "full_corpus|recent|project_specific",
  "project": "string (if project_specific)"
}
```

**Response:**
```json
{
  "gaps_detected": [
    {
      "gap_type": "unconnected_concepts|unanswered_question|unexplored_implication",
      "description": "string",
      "related_concepts": ["string"],
      "relevant_documents": ["uuid"],
      "potential_value": "high|medium|low",
      "suggested_exploration": "string"
    }
  ],
  "analysis_timestamp": "ISO 8601"
}
```

### 4.2 Surface Forgotten Gems

```http
POST /proactive/forgotten-gems
```

**Request Body:**
```json
{
  "context": {
    "current_focus": "string",
    "timeframe": "last_accessed_before_ISO_8601"
  }
}
```

**Response:**
```json
{
  "forgotten_content": [
    {
      "document_id": "uuid",
      "title": "string",
      "excerpt": "string",
      "last_accessed": "ISO 8601",
      "relevance_to_current_context": "string",
      "why_surfaced": "string",
      "potential_connections": ["concept"]
    }
  ]
}
```

### 4.3 Track Evolution

```http
GET /proactive/evolution/{concept}
```

**Response:**
```json
{
  "concept": "string",
  "evolution_timeline": [
    {
      "document_id": "uuid",
      "date": "ISO 8601",
      "articulation": "string",
      "stage": "initial|developing|mature|transformed",
      "key_shifts": ["string"]
    }
  ],
  "synthesis_opportunity": {
    "exists": true,
    "reason": "string",
    "scattered_insights": ["document_id"],
    "suggested_synthesis": "string"
  }
}
```

### 4.4 Request Synthesis

```http
POST /proactive/synthesize
```

**Request Body:**
```json
{
  "synthesis_type": "concept|question|project|timeframe",
  "target": {
    "concept": "string",
    "question": "string",
    "project": "string",
    "timeframe": {
      "start": "ISO 8601",
      "end": "ISO 8601"
    }
  },
  "depth": "summary|comprehensive|academic"
}
```

**Response:**
```json
{
  "synthesis": {
    "overview": "string",
    "key_insights": ["string"],
    "evolution": "string",
    "contradictions_reconciled": [
      {
        "tension": "string",
        "resolution": "string"
      }
    ],
    "open_questions": ["string"],
    "strongest_articulations": ["document_id"],
    "suggested_next_steps": ["string"]
  },
  "sources": ["document_id"],
  "generated_at": "ISO 8601"
}
```

---

## 5. Analysis & Maintenance

### 5.1 Analyze Corpus

```http
POST /analysis/corpus
```

**Request Body:**
```json
{
  "analysis_types": [
    "concept_extraction",
    "cross_references",
    "temporal_evolution",
    "cluster_detection"
  ],
  "scope": "full|incremental_since_timestamp"
}
```

**Response:**
```json
{
  "status": "completed",
  "analysis_id": "uuid",
  "results": {
    "new_concepts_extracted": 0,
    "cross_references_detected": 0,
    "concept_clusters": [
      {
        "cluster_label": "string",
        "concepts": ["string"],
        "coherence_score": 0.85
      }
    ],
    "evolution_chains_updated": 0
  },
  "processing_time_ms": 0,
  "recommendations": ["string"]
}
```

### 5.2 Validate State

```http
POST /analysis/validate-state
```

**Response:**
```json
{
  "validation_results": {
    "intellectual_map": {
      "valid": true,
      "issues": ["string"],
      "suggestions": ["string"]
    },
    "cross_corpus_understanding": {
      "valid": true,
      "outdated_entries": ["string"],
      "missing_connections": ["string"]
    },
    "inconsistencies": [
      {
        "type": "contradictory_claims|orphaned_concepts|broken_references",
        "description": "string",
        "affected_items": ["string"]
      }
    ]
  },
  "recommended_actions": ["string"]
}
```

### 5.3 Export Data

```http
POST /export
```

**Request Body:**
```json
{
  "export_type": "full_corpus|intellectual_map|session_history|concept_graph",
  "format": "json|markdown|csv|graphml",
  "filters": {
    "date_range": {
      "start": "ISO 8601",
      "end": "ISO 8601"
    },
    "projects": ["string"]
  }
}
```

**Response:**
```json
{
  "export_id": "uuid",
  "status": "processing|completed",
  "download_url": "string (when completed)",
  "expires_at": "ISO 8601"
}
```

---

## 6. Webhooks (Optional)

### 6.1 Register Webhook

```http
POST /webhooks
```

**Request Body:**
```json
{
  "url": "string",
  "events": [
    "document.ingested",
    "synthesis.available",
    "gap.detected",
    "state.updated"
  ],
  "secret": "string (for signature verification)"
}
```

**Webhook Payload Format:**
```json
{
  "event": "document.ingested",
  "timestamp": "ISO 8601",
  "data": {
    "document_id": "uuid",
    "title": "string",
    "concepts_extracted": ["string"]
  },
  "signature": "hmac_sha256"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {
      "field": "Additional context"
    },
    "request_id": "uuid"
  }
}
```

**Common Error Codes:**
- `INVALID_REQUEST`: Malformed request body
- `NOT_FOUND`: Resource doesn't exist
- `PROCESSING_FAILED`: Background job failed
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `AUTHENTICATION_REQUIRED`: Missing or invalid token
- `VALIDATION_ERROR`: Invalid data in request

---

## Rate Limits

- Ingestion: 100 documents/hour
- Query: 1000 requests/hour
- Analysis: 10 requests/hour
- Export: 5 requests/hour

Rate limit headers included in all responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640000000
```