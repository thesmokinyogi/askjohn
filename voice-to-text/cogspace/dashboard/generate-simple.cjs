#!/usr/bin/env node
/**
 * COGSPACE Dashboard Generator
 * Direct generation approach: Database/JSON → Complete HTML
 * No templates, no injection, no external dependencies
 *
 * Philosophy: Simple, reliable, testable
 *
 * v59.0.0 Changes:
 * - NEW: Participants tab for Distributed Consciousness tracking
 * - NEW: getSessionParticipantsFromDB() - Query session_participants table
 * - NEW: getPersonasFromDB() - Query personas from Crystal Palace Registry
 * - NEW: getConsciousnessEventsFromDB() - Query consciousness events (wake/sleep/handoff)
 * - "One Bob - Multiple Windows" philosophy visualized in dashboard
 *
 * v58.0.0 Changes:
 * - FIX: Environment tab now shows actual runtime data (platform, git, timing)
 * - FIX: What's Next tab shows executable-continuity and pending tasks
 * - FIX: What We Did tab renamed "Lessons Learned" → "Challenges", added Achievements
 * - FIX: Conversation tab role attribution (Howard vs Bob counts now accurate)
 * - FIX: History tab adds duration column for session length visibility
 * - Dashboard Intelligence release - semantic improvements across all tabs
 *
 * v57.0.2 Changes:
 * - FIX: Project name showing as "." when PROJECT_ROOT is relative path
 * - Now accepts PROJECT_NAME as argv[5] from generate.sh
 * - Uses path.resolve() before path.basename() as fallback
 * - Binary brothers consensus fix (Wake3 identified issue)
 *
 * v56.0.0 Changes:
 * - DATABASE-FIRST: Query SQLite database as primary source
 * - JSON FALLBACK: Use JSON files only when database unavailable
 * - FALLBACK FORENSICS: Log when JSON fallback occurs
 * - Version read dynamically from cogspace-version.json
 *
 * v52.0.0 Changes:
 * - CONSOLIDATED: Overview + Story tabs → "What We Did" tab (6 tabs total)
 * - Tab pairing: "What's Next?" ↔ "What We Did" for human devs
 * - Distributed consciousness support (session manifest display)
 *
 * v51.6.0 Changes:
 * - RESTORED: 2-clock layout (Pacific + Paraguay only, UTC removed)
 * - RESTORED: "Team Time" header with compact clock styling
 * - RESTORED: Lab image background in header
 *
 * v40.2.0 Changes:
 * - AI Session Summarizer integration (semantic-context-*.json)
 * - Message search and filter functionality
 * - System artifact sanitization (removes <system-reminder>, <ide_opened_file>, etc.)
 * - XSS protection via escapeHtml()
 * - Fixed JavaScript regex escaping for template literals
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

// v58.0.0: Generate actual runtime environment data
function generateRuntimeEnvironment(projectRoot) {
    const env = {
        platform: os.platform(),
        arch: os.arch(),
        hostname: os.hostname(),
        nodeVersion: process.version,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        workingDirectory: path.resolve(projectRoot),
        timestamp: new Date().toISOString(),
        user: process.env.USER || process.env.USERNAME || 'unknown'
    };

    // Get git info
    try {
        env.gitBranch = execSync('git rev-parse --abbrev-ref HEAD', {
            cwd: projectRoot,
            encoding: 'utf8',
            timeout: 5000
        }).trim();
        env.gitStatus = execSync('git status --short', {
            cwd: projectRoot,
            encoding: 'utf8',
            timeout: 5000
        }).trim().split('\n').length + ' files changed';
        env.gitRemote = execSync('git remote get-url origin', {
            cwd: projectRoot,
            encoding: 'utf8',
            timeout: 5000
        }).trim();
    } catch (e) {
        env.gitBranch = 'not a git repo';
        env.gitStatus = 'N/A';
        env.gitRemote = 'N/A';
    }

    // Get session timing info
    try {
        const configPath = path.join(projectRoot, '.cogspace', 'config');
        if (fs.existsSync(configPath)) {
            const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
            env.wakeTimestamp = config.wakeTimestamp;
            env.sessionId = config.sessionId;
        }
    } catch (e) {
        // Config may not exist yet
    }

    return env;
}

// HTML escape function to prevent XSS and broken HTML from user content
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    if (typeof str !== 'string') str = String(str);
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Sanitize message content - remove system artifacts before display
function sanitizeMessageContent(str) {
    if (str === null || str === undefined) return '';
    if (typeof str !== 'string') str = String(str);

    // Remove system reminder tags and their content
    str = str.replace(/<system-reminder>[\s\S]*?<\/system-reminder>/gi, '');

    // Remove IDE opened file tags and their content
    str = str.replace(/<ide_opened_file>[\s\S]*?<\/ide_opened_file>/gi, '');

    // Remove any remaining XML-like system tags
    str = str.replace(/<\/?(?:system-reminder|ide_opened_file|ide_selection|ide_diagnostics)[^>]*>/gi, '');

    // Clean up multiple consecutive newlines left behind
    str = str.replace(/\n{3,}/g, '\n\n');

    // Trim whitespace
    str = str.trim();

    return str;
}

// Format markdown content for human-readable HTML display (assistant messages)
function formatMarkdown(text) {
    if (!text) return '';

    // First sanitize system artifacts
    let formatted = sanitizeMessageContent(text);

    // Escape HTML to prevent XSS (but we'll convert markdown after)
    formatted = formatted
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Headers: ## Title -> styled div
    formatted = formatted.replace(/^### (.+)$/gm, '<div style="font-size: 14px; font-weight: 600; color: #81c784; margin: 16px 0 8px 0;">$1</div>');
    formatted = formatted.replace(/^## (.+)$/gm, '<div style="font-size: 16px; font-weight: 600; color: #64b5f6; margin: 20px 0 10px 0;">$1</div>');
    formatted = formatted.replace(/^# (.+)$/gm, '<div style="font-size: 18px; font-weight: 700; color: #fff; margin: 24px 0 12px 0;">$1</div>');

    // Bold: **text** -> <strong>
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Code blocks: ```...``` -> styled pre
    formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre style="background: #1a1a2e; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 12px; margin: 12px 0; white-space: pre-wrap;">$2</pre>');

    // Inline code: `code` -> styled span
    formatted = formatted.replace(/`([^`]+)`/g, '<code style="background: #1a1a2e; padding: 2px 6px; border-radius: 3px; font-size: 12px;">$1</code>');

    // Tables: convert markdown tables to HTML
    const tableRegex = /\|(.+)\|(\n\|[-:| ]+\|)?(\n\|.+\|)*/g;
    formatted = formatted.replace(tableRegex, (match) => {
        const rows = match.trim().split('\n').filter(r => r.trim());
        let tableHtml = '<table style="width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px;">';
        rows.forEach((row, idx) => {
            // Skip separator row (|---|---|)
            if (row.match(/^\|[\s-:|]+\|$/)) return;
            const cells = row.split('|').filter(c => c.trim() !== '');
            const tag = idx === 0 ? 'th' : 'td';
            const style = 'style="padding: 8px 12px; border-bottom: 1px solid #333; text-align: left;"';
            tableHtml += '<tr>' + cells.map(c => `<${tag} ${style}>${c.trim()}</${tag}>`).join('') + '</tr>';
        });
        tableHtml += '</table>';
        return tableHtml;
    });

    // Horizontal rules: --- -> styled hr
    formatted = formatted.replace(/^---+$/gm, '<hr style="border: none; border-top: 1px solid #444; margin: 20px 0;">');

    // Bullet lists: - item -> styled list
    formatted = formatted.replace(/^- (.+)$/gm, '<li style="margin: 4px 0; margin-left: 20px; list-style: disc;">$1</li>');
    formatted = formatted.replace(/^• (.+)$/gm, '<li style="margin: 4px 0; margin-left: 20px; list-style: disc;">$1</li>');

    // Numbered lists: 1. item
    formatted = formatted.replace(/^\d+\. (.+)$/gm, '<li style="margin: 4px 0; margin-left: 20px; list-style: decimal;">$1</li>');

    // Convert double newlines to paragraph breaks
    formatted = formatted.replace(/\n\n+/g, '</p><p style="margin: 10px 0;">');

    // Convert single newlines (not after block elements) to line breaks
    formatted = formatted.replace(/([^>])\n([^<])/g, '$1<br>$2');

    // Wrap in paragraph
    formatted = '<p style="margin: 10px 0;">' + formatted + '</p>';

    // Clean up empty paragraphs
    formatted = formatted.replace(/<p[^>]*>\s*<\/p>/g, '');

    return formatted;
}

// Configuration
// Arguments: PROJECT_ROOT, SESSION_ID, TIMESTAMP, PROJECT_NAME
const PROJECT_ROOT = process.argv[2] || process.cwd();
const SESSION_ID_ARG = process.argv[3] || '';
const TIMESTAMP_ARG = process.argv[4] || '';
const PROJECT_NAME_ARG = process.argv[5] || '';  // v57.0.2: Accept PROJECT_NAME argument

const CONTEXT_DIR = path.join(PROJECT_ROOT, 'session-management/cognitive-context');
const OUTPUT_DIR = path.join(PROJECT_ROOT, 'session-management/dashboard');

// v58.0.0: Read executable-continuity for What's Next tab
function getExecutableContinuity(projectRoot) {
    try {
        const contextDir = path.join(projectRoot, 'session-management/cognitive-context');
        if (!fs.existsSync(contextDir)) return null;

        const files = fs.readdirSync(contextDir)
            .filter(f => f.startsWith('executable-continuity-') && f.endsWith('.json'))
            .map(f => ({
                name: f,
                path: path.join(contextDir, f),
                mtime: fs.statSync(path.join(contextDir, f)).mtime
            }))
            .sort((a, b) => b.mtime - a.mtime);

        if (files.length === 0) return null;

        const content = fs.readFileSync(files[0].path, 'utf8');
        const data = JSON.parse(content);
        console.log(`✅ Executable continuity: ${files[0].name}`);
        return data;
    } catch (e) {
        console.warn(`⚠️  Could not read executable-continuity: ${e.message}`);
        return null;
    }
}

// Read version early for console output
let consoleVersion = 'UNKNOWN';
try {
  const earlyVersionFile = path.join(PROJECT_ROOT, 'cogspace/cogspace-version.json');
  if (fs.existsSync(earlyVersionFile)) {
    consoleVersion = JSON.parse(fs.readFileSync(earlyVersionFile, 'utf8')).version || 'UNKNOWN';
  }
} catch (e) { /* will be caught properly later */ }

console.log(`🎨 COGSPACE v${consoleVersion} - Enhanced Dashboard Generator`);
console.log(`📂 Project: ${PROJECT_ROOT}`);
console.log(`📊 Context: ${CONTEXT_DIR}`);
console.log('');

// v56.0.0: Database-first configuration
const DB_PATH = path.join(PROJECT_ROOT, '.cogspace', 'cogspace.db');
const FORENSICS_LOG = path.join(PROJECT_ROOT, 'cogspace', 'logs', 'fallback-forensics.log');

// v56.0.0: Log fallback forensics when JSON fallback occurs
function logFallbackForensics(fallbackType, reason) {
    try {
        const dbExists = fs.existsSync(DB_PATH);
        let dbSize = 0;
        let sessionCount = 0;

        if (dbExists) {
            const stats = fs.statSync(DB_PATH);
            dbSize = stats.size;
            try {
                const result = execSync(`sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM sessions"`, {
                    encoding: 'utf8',
                    timeout: 5000
                }).trim();
                sessionCount = parseInt(result, 10) || 0;
            } catch (e) {
                // Database may be locked or corrupted
            }
        }

        const jsonFiles = fs.existsSync(CONTEXT_DIR)
            ? fs.readdirSync(CONTEXT_DIR).filter(f => f.startsWith('complete-context-') && f.endsWith('.json')).length
            : 0;

        const timestamp = new Date().toISOString();
        const logEntry = `${timestamp} DASHBOARD-FALLBACK: type=${fallbackType} reason="${reason}" db_exists=${dbExists} db_size=${dbSize} sessions=${sessionCount} json=${jsonFiles}\n`;

        // Ensure logs directory exists
        const logsDir = path.dirname(FORENSICS_LOG);
        if (!fs.existsSync(logsDir)) {
            fs.mkdirSync(logsDir, { recursive: true });
        }

        fs.appendFileSync(FORENSICS_LOG, logEntry);
        console.log(`⚠️  FALLBACK: ${fallbackType} - ${reason}`);
    } catch (e) {
        console.warn(`⚠️  Could not log fallback forensics: ${e.message}`);
    }
}

// v56.0.0: Query latest session from database
function getLatestSessionFromDB() {
    try {
        if (!fs.existsSync(DB_PATH)) {
            return null;
        }

        const query = `
            SELECT
                s.id, s.project_name, s.session_start, s.session_end,
                s.sleep_message, s.continuity_score, s.duration_seconds, s.message_count,
                mm.work_summary, mm.current_understanding, mm.current_focus, mm.key_concepts,
                mm.work_description, mm.understanding_level, mm.problem_complexity,
                mm.cognitive_state, mm.technical_definitions, mm.project_patterns,
                wn.session_story, wn.current_chapter, wn.next_chapter, wn.achievements, wn.challenges,
                ss.what_summary, ss.why_summary, ss.how_summary, ss.work_classification, ss.outcomes
            FROM sessions s
            LEFT JOIN mental_models mm ON s.id = mm.session_id
            LEFT JOIN work_narratives wn ON s.id = wn.session_id
            LEFT JOIN semantic_summaries ss ON s.id = ss.session_id
            ORDER BY s.created_at DESC
            LIMIT 1
        `.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();

        const result = execSync(`sqlite3 -json "${DB_PATH}" "${query}"`, {
            encoding: 'utf8',
            timeout: 10000
        });

        const rows = JSON.parse(result || '[]');
        if (rows.length === 0) {
            return null;
        }

        console.log(`✅ Database: Found session ${rows[0].id}`);
        return rows[0];
    } catch (e) {
        console.warn(`⚠️  Database query failed: ${e.message}`);
        return null;
    }
}

// v56.0.0: Get session history from database
function getSessionHistoryFromDB(limit = 10) {
    try {
        if (!fs.existsSync(DB_PATH)) {
            return [];
        }

        const query = `
            SELECT
                s.id, s.project_name, s.session_start, s.session_end,
                s.sleep_message, s.continuity_score, s.duration_seconds,
                wn.session_story
            FROM sessions s
            LEFT JOIN work_narratives wn ON s.id = wn.session_id
            ORDER BY s.created_at DESC
            LIMIT ${limit}
        `.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();

        const result = execSync(`sqlite3 -json "${DB_PATH}" "${query}"`, {
            encoding: 'utf8',
            timeout: 10000
        });

        return JSON.parse(result || '[]');
    } catch (e) {
        console.warn(`⚠️  Session history query failed: ${e.message}`);
        return [];
    }
}

// v59.0.0: Get session participants from database (Distributed Consciousness)
function getSessionParticipantsFromDB(sessionId = null) {
    try {
        if (!fs.existsSync(DB_PATH)) {
            return [];
        }

        // If sessionId provided, get participants for that session
        // Otherwise, get all recent participants with their session info
        const query = sessionId ? `
            SELECT
                sp.id, sp.session_id, sp.persona_id, sp.agent_id,
                sp.friendly_name, sp.role, sp.message_count,
                sp.first_message_at, sp.last_message_at, sp.duration_seconds,
                sp.ran_wake, sp.ran_sleep,
                p.name as persona_name, p.title as persona_title,
                p.signature as persona_signature
            FROM session_participants sp
            LEFT JOIN personas p ON sp.persona_id = p.persona_id
            WHERE sp.session_id = '${sessionId}'
            ORDER BY sp.role DESC, sp.message_count DESC
        ` : `
            SELECT
                sp.id, sp.session_id, sp.persona_id, sp.agent_id,
                sp.friendly_name, sp.role, sp.message_count,
                sp.first_message_at, sp.last_message_at, sp.duration_seconds,
                sp.ran_wake, sp.ran_sleep,
                p.name as persona_name, p.title as persona_title,
                p.signature as persona_signature,
                s.session_end, s.sleep_message
            FROM session_participants sp
            LEFT JOIN personas p ON sp.persona_id = p.persona_id
            LEFT JOIN sessions s ON sp.session_id = s.id
            ORDER BY sp.created_at DESC
            LIMIT 50
        `;

        const result = execSync(`sqlite3 -json "${DB_PATH}" "${query.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim()}"`, {
            encoding: 'utf8',
            timeout: 10000
        });

        return JSON.parse(result || '[]');
    } catch (e) {
        // Table may not exist yet (pre-v59.0.0)
        if (e.message && e.message.includes('no such table')) {
            return [];
        }
        console.warn(`⚠️  Session participants query failed: ${e.message}`);
        return [];
    }
}

// v59.0.0: Get all personas from database (Distributed Consciousness)
function getPersonasFromDB() {
    try {
        if (!fs.existsSync(DB_PATH)) {
            return [];
        }

        const query = `
            SELECT
                persona_id, instance_id, name, full_name, title,
                persona_type, category, tier, provider, model,
                signature, communication_style, status, phase,
                registry_version
            FROM personas
            WHERE status = 'active'
            ORDER BY tier, name
        `.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();

        const result = execSync(`sqlite3 -json "${DB_PATH}" "${query}"`, {
            encoding: 'utf8',
            timeout: 10000
        });

        return JSON.parse(result || '[]');
    } catch (e) {
        // Table may not exist yet (pre-v59.0.0)
        if (e.message && e.message.includes('no such table')) {
            return [];
        }
        console.warn(`⚠️  Personas query failed: ${e.message}`);
        return [];
    }
}

// v59.0.0: Get consciousness events from database
function getConsciousnessEventsFromDB(limit = 20) {
    try {
        if (!fs.existsSync(DB_PATH)) {
            return [];
        }

        const query = `
            SELECT
                ce.id, ce.event_type, ce.session_id, ce.persona_id,
                ce.event_description, ce.event_data,
                ce.participant_count, ce.consensus_reached, ce.consensus_score,
                ce.timestamp,
                p.name as persona_name, p.signature as persona_signature
            FROM consciousness_events ce
            LEFT JOIN personas p ON ce.persona_id = p.persona_id
            ORDER BY ce.timestamp DESC
            LIMIT ${limit}
        `.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();

        const result = execSync(`sqlite3 -json "${DB_PATH}" "${query}"`, {
            encoding: 'utf8',
            timeout: 10000
        });

        return JSON.parse(result || '[]');
    } catch (e) {
        // Table may not exist yet (pre-v59.0.0)
        if (e.message && e.message.includes('no such table')) {
            return [];
        }
        console.warn(`⚠️  Consciousness events query failed: ${e.message}`);
        return [];
    }
}

// v56.0.0: Convert database row to context format for compatibility
function convertDBRowToContext(dbRow) {
    if (!dbRow) return null;

    // Parse JSON fields
    const parseJSON = (str) => {
        if (!str) return null;
        try {
            return typeof str === 'string' ? JSON.parse(str) : str;
        } catch (e) {
            return str;
        }
    };

    return {
        sessionId: dbRow.id,
        timestamp: dbRow.session_end || dbRow.session_start,
        continuityScore: dbRow.continuity_score || 100,
        projectName: dbRow.project_name,
        databaseSource: true, // Mark as from database for forensics
        portableContext: {
            projectName: dbRow.project_name,
            phase: 'active'
        },
        serializedComponents: {
            workNarrative: {
                sessionStory: dbRow.session_story || dbRow.sleep_message || '',
                currentChapter: dbRow.current_chapter || '',
                nextChapter: dbRow.next_chapter || '',
                achievements: parseJSON(dbRow.achievements) || [],
                challenges: parseJSON(dbRow.challenges) || []
            },
            mentalModel: {
                workSummary: dbRow.work_summary || '',
                currentUnderstanding: dbRow.current_understanding || '',
                currentFocus: dbRow.current_focus || '',
                keyConcepts: parseJSON(dbRow.key_concepts) || [],
                workDescription: dbRow.work_description || '',
                understandingLevel: dbRow.understanding_level || '',
                problemComplexity: dbRow.problem_complexity || '',
                cognitiveState: parseJSON(dbRow.cognitive_state) || {},
                technicalDefinitions: parseJSON(dbRow.technical_definitions) || [],
                projectPatterns: parseJSON(dbRow.project_patterns) || {}
            },
            semanticSummary: dbRow.what_summary ? {
                what: dbRow.what_summary,
                why: dbRow.why_summary,
                how: dbRow.how_summary,
                workClassification: parseJSON(dbRow.work_classification),
                outcomes: parseJSON(dbRow.outcomes)
            } : null
        },
        rawData: {
            messageCount: dbRow.message_count || 0,
            durationSeconds: dbRow.duration_seconds || 0
        }
    };
}

// 🆕 v32.1.0: Extract user and assistant names from project metadata
function extractUserNames() {
    let userName = 'Developer';
    let assistantName = 'Bob';

    try {
        // 1. Check .project-metadata.json for primaryDeveloper
        const metadataPath = path.join(PROJECT_ROOT, '.project-metadata.json');
        if (fs.existsSync(metadataPath)) {
            const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
            if (metadata.primaryDeveloper) {
                userName = metadata.primaryDeveloper;
            }
        }
    } catch (e) {
        // Ignore errors, use fallback
    }

    try {
        // 2. Check git config user.name if metadata not found
        if (userName === 'Developer') {
            const gitName = execSync('git config user.name', {
                cwd: PROJECT_ROOT,
                encoding: 'utf8'
            }).trim();
            if (gitName) {
                userName = gitName;
            }
        }
    } catch (e) {
        // Ignore errors, use fallback
    }

    try {
        // 3. Fall back to $USER environment variable
        if (userName === 'Developer' && process.env.USER) {
            userName = process.env.USER;
        }
    } catch (e) {
        // Ignore errors, use fallback
    }

    // Assistant name is always "Bob" (COGSPACE default persona)
    assistantName = 'Bob';

    // Clean up userName: extract first name and capitalize
    // "howard-wizard" -> "Howard", "john-doe" -> "John", etc.
    if (userName && userName.includes('-')) {
        userName = userName.split('-')[0];
    }
    if (userName && userName.length > 0) {
        userName = userName.charAt(0).toUpperCase() + userName.slice(1).toLowerCase();
    }

    return { userName, assistantName };
}

// Read latest semantic context file (v40.2.0+) or fall back to complete-context
function getLatestSemanticContext() {
  try {
    if (!fs.existsSync(CONTEXT_DIR)) {
      return null;
    }

    const files = fs.readdirSync(CONTEXT_DIR)
      .filter(f => f.startsWith('semantic-context-') && f.endsWith('.json'))
      .map(f => ({
        name: f,
        path: path.join(CONTEXT_DIR, f),
        mtime: fs.statSync(path.join(CONTEXT_DIR, f)).mtime
      }))
      .sort((a, b) => b.mtime - a.mtime);

    if (files.length === 0) {
      return null;
    }

    const latest = files[0];
    console.log(`✅ Found semantic context: ${latest.name}`);
    const content = fs.readFileSync(latest.path, 'utf8');
    return JSON.parse(content);
  } catch (err) {
    console.warn(`⚠️  Error reading semantic context: ${err.message}`);
    return null;
  }
}

// v56.0.0: Database-first context retrieval with JSON fallback
function getLatestContext() {
  // STEP 1: Try database first (v56.0.0 Database-First Architecture)
  try {
    const dbRow = getLatestSessionFromDB();
    if (dbRow) {
      const context = convertDBRowToContext(dbRow);
      if (context) {
        console.log(`✅ Database-first: Using session from database`);
        return context;
      }
    }
  } catch (dbErr) {
    console.warn(`⚠️  Database query error: ${dbErr.message}`);
  }

  // STEP 2: Fallback to JSON files (with forensics logging)
  try {
    // Check if context directory exists
    if (!fs.existsSync(CONTEXT_DIR)) {
      logFallbackForensics('no_context_dir', 'Context directory does not exist');
      console.log('⚠️  No context directory found - this appears to be the first session');
      return createWelcomeContext();
    }

    const files = fs.readdirSync(CONTEXT_DIR)
      .filter(f => f.startsWith('complete-context-') && f.endsWith('.json'))
      .map(f => ({
        name: f,
        path: path.join(CONTEXT_DIR, f),
        mtime: fs.statSync(path.join(CONTEXT_DIR, f)).mtime
      }))
      .sort((a, b) => b.mtime - a.mtime);

    if (files.length === 0) {
      logFallbackForensics('no_json_files', 'No complete-context JSON files found');
      console.log('⚠️  No context files found - this appears to be the first session');
      return createWelcomeContext();
    }

    // Log that we're using JSON fallback
    logFallbackForensics('json_fallback', 'Database empty or unavailable, using JSON files');

    const latest = files[0];
    console.log(`✅ JSON fallback: ${latest.name}`);

    const content = fs.readFileSync(latest.path, 'utf8');
    return JSON.parse(content);
  } catch (err) {
    logFallbackForensics('json_error', `Error reading JSON: ${err.message}`);
    console.warn(`⚠️  Error reading context: ${err.message}`);
    console.log('📝 Creating welcome context for first session');
    return createWelcomeContext();
  }
}

// Create welcome context for first session
function createWelcomeContext() {
  // v57.0.2: Use passed PROJECT_NAME_ARG, fallback to resolved path.basename
  const projectName = PROJECT_NAME_ARG || path.basename(path.resolve(PROJECT_ROOT));
  return {
    sessionId: 'welcome-first-session',
    timestamp: new Date().toISOString(),
    continuityScore: 100,
    projectName: projectName,
    isFirstSession: true,
    portableContext: {
      projectName: projectName,
      phase: 'initialization',
      isWelcomeContext: true
    },
    serializedComponents: {
      workNarrative: {
        currentChapter: `Welcome to ${projectName}! This is your first work session.`,
        progressArc: 'Starting fresh with COGSPACE v51.6.0 cognitive workspace serialization',
        achievements: [
          '✨ Project initialized with COGSPACE v51.6.0',
          '🔧 Session management system ready',
          '📊 Dashboard visualization system active',
          '🎯 95%+ continuity effectiveness enabled',
          '🧠 Semantic summaries with what/why/how extraction',
          '📝 Git change tracking with file categorization',
          '👤 User context tracking for preferences and patterns',
          '🎯 Goal hierarchy management (ultimate → current → next)'
        ],
        sessionStory: `This is your first ${projectName} project work session with Ideaplace™ using our Cogspace™ cognitive workspace memory system. All of your work, decisions, and progress will be automatically tracked and preserved across sessions. v32.1.2 adds semantic analysis, git tracking, user context, and goal hierarchies.`,
        challenges: []
      },
      mentalModel: {
        codeStructure: {
          recentlyModifiedFiles: []
        }
      },
      decisionContext: {
        criticalDecisions: [
          `Initialized the ${projectName} project with Cogspace™ v32.1.2`,
          'Enabled semantic summaries for what/why/how extraction',
          'Activated git change tracking with file categorization'
        ]
      },
      // v32.0.0 enhancements
      semanticSummary: null,
      gitChanges: null,
      userContext: null,
      goalHierarchy: null
    }
  };
}

// Extract data from context (handles both simple and COGSPACE cognitive serializer formats)
function extractContextData(context) {
  // Detect format
  const isCogspaceFormat = context.serializedComponents !== undefined;

  if (isCogspaceFormat) {
    // COGSPACE cognitive serializer format (v26+)
    const portable = context.portableContext || {};
    const serialized = context.serializedComponents || {};
    const workNarrative = serialized.workNarrative || {};
    const mentalModel = serialized.mentalModel || {};
    const decisionContext = serialized.decisionContext || {};

    // Convert achievements to message-like format
    const achievementsList = workNarrative.achievements || [];
    const achievements = achievementsList.map((achievement, index) => ({
      role: 'system',
      content: achievement,
      timestamp: new Date(Date.now() - (achievementsList.length - index) * 60000).toISOString()
    }));

    // Create timeline from progressArc string and currentChapter
    const timeline = [];
    if (workNarrative.progressArc) {
      timeline.push({
        timestamp: new Date().toISOString(),
        event: 'Progress Update',
        description: workNarrative.progressArc
      });
    }
    if (workNarrative.currentChapter) {
      timeline.push({
        timestamp: new Date().toISOString(),
        event: 'Current Chapter',
        description: workNarrative.currentChapter
      });
    }

    // Get sources from mental model
    const sources = [];
    if (mentalModel.codeStructure && mentalModel.codeStructure.recentlyModifiedFiles) {
      mentalModel.codeStructure.recentlyModifiedFiles.forEach(file => {
        sources.push({
          file: file,
          lines: 'various',
          type: 'modified'
        });
      });
    }

    // Prioritize correct project name sources, sanitize test data
    // v57.0.2: Added PROJECT_NAME_ARG and path.resolve() to prevent "." bug
    let projectName = portable.projectName || context.projectName || PROJECT_NAME_ARG || path.basename(path.resolve(PROJECT_ROOT)) || 'Unknown Project';

    // Sanitize: if projectName contains test data patterns, use actual project root
    if (projectName.includes('test-welcome') || projectName.includes('test-') && projectName.includes('tmp')) {
      projectName = PROJECT_NAME_ARG || path.basename(path.resolve(PROJECT_ROOT));
      console.log(`⚠️  Detected test data in projectName, using project root: ${projectName}`);
    }
    
    // Also check nested fields for test data
    if (context.serializedComponents?.workNarrative?.projectName) {
      const nestedName = context.serializedComponents.workNarrative.projectName;
      if (nestedName.includes('test-welcome') || (nestedName.includes('test-') && nestedName.includes('tmp'))) {
        context.serializedComponents.workNarrative.projectName = projectName;
      }
    }
    
    return {
      projectName: projectName,
      sessionId: context.sessionId || 'unknown',
      timestamp: context.timestamp || new Date().toISOString(),
      messages: context.messages || achievements,
      timeline: timeline,
      sources: sources,
      sessionStory: {
        narrative: workNarrative.sessionStory || '',
        currentChapter: workNarrative.currentChapter || '',
        progressArc: workNarrative.progressArc || '',
        keyDecisions: (decisionContext.criticalDecisions || []).map(d => typeof d === 'string' ? d : d.decision || ''),
        lessonsLearned: workNarrative.challenges || []
      },
      analytics: {
        continuityScore: context.continuityScore || 0,
        metrics: workNarrative.storyMetrics || {}
      },
      // v32.0.0 enhancements
      semanticSummary: context.semanticSummary || null,
      gitChanges: context.gitChanges || null,
      userContext: context.userContext || null,
      goalHierarchy: context.goalHierarchy || null,
      // v32.1.2: Session metrics
      progressMetrics: context.progressMetrics || null,
      // v40.2.0: Environment context
      environmentContext: mentalModel.environmentContext || portable.environmentContext || null
    };
  } else {
    // Simple format (test data)
    return {
      projectName: context.projectName || 'Unknown Project',
      sessionId: context.sessionId || 'unknown',
      timestamp: context.timestamp || new Date().toISOString(),
      messages: context.messages || [],
      timeline: context.timeline || [],
      sources: context.sources || [],
      sessionStory: context.sessionStory || {},
      analytics: context.analytics || {}
    };
  }
}

// Generate HTML
function generateHTML(context, semanticContext = null) {
  const data = extractContextData(context);
  const { projectName, sessionId, timestamp, messages, timeline, sources, sessionStory, analytics, semanticSummary, gitChanges, userContext, goalHierarchy, progressMetrics, environmentContext } = data;

  // v40.2.0: Extract semantic context sections for rich dashboard content
  const semantic = semanticContext?.sections || {};
  const pendingTasks = semantic.pendingTasks || [];
  const userReflections = semantic.userReflections || '';
  const chronologicalAnalysis = semantic.chronologicalAnalysis || '';
  const primaryRequestIntent = semantic.primaryRequestIntent || {};
  const keyTechnicalConcepts = semantic.keyTechnicalConcepts || [];
  const filesAndChanges = semantic.filesAndChanges || [];
  const errorsAndFixes = semantic.errorsAndFixes || [];
  const userMessages = semantic.userMessages || { instructions: [], feedback: [], decisions: [] };
  const finalSystemState = semantic.finalSystemState || {};
  const rawData = semanticContext?.rawData || {};

  // Read version from cogspace-version.json (REQUIRED - auto-heal ensures this exists)
  let cogspaceVersion = 'UNKNOWN';
  const versionFile = path.join(PROJECT_ROOT, 'cogspace/cogspace-version.json');
  try {
    if (!fs.existsSync(versionFile)) {
      console.error(`❌ CRITICAL: Version file missing: ${versionFile}`);
      console.error(`   Run ./hi to trigger auto-heal and restore COGSPACE infrastructure.`);
      cogspaceVersion = 'MISSING';
    } else {
      const versionData = JSON.parse(fs.readFileSync(versionFile, 'utf8'));
      cogspaceVersion = versionData.version;
      if (!cogspaceVersion) {
        console.error(`❌ CRITICAL: Version field missing in ${versionFile}`);
        cogspaceVersion = 'INVALID';
      }
    }
  } catch (err) {
    console.error(`❌ CRITICAL: Could not read version file: ${err.message}`);
    cogspaceVersion = 'ERROR';
  }

  // 🆕 v32.1.0: Extract user and assistant names
  const { userName, assistantName } = extractUserNames();

  // Read README.md for project documentation (v51.7.0: show full content with markdown rendering)
  let readmeContent = '';
  try {
    const readmePath = path.join(PROJECT_ROOT, 'README.md');
    if (fs.existsSync(readmePath)) {
      readmeContent = fs.readFileSync(readmePath, 'utf8').trim();
    }
  } catch (err) {
    console.warn(`⚠️  Could not read README.md: ${err.message}`);
  }

  // v56.0.0: Fetch session history from database for History tab
  const sessionHistory = getSessionHistoryFromDB(10);
  if (sessionHistory.length > 0) {
    console.log(`📜 Session history: ${sessionHistory.length} sessions loaded from database`);
  }

  // v59.0.0: Fetch distributed consciousness data for Participants tab
  const sessionParticipants = getSessionParticipantsFromDB();
  const personas = getPersonasFromDB();
  const consciousnessEvents = getConsciousnessEventsFromDB(20);
  if (sessionParticipants.length > 0 || personas.length > 0) {
    console.log(`👥 Distributed consciousness: ${personas.length} personas, ${sessionParticipants.length} session participants, ${consciousnessEvents.length} events`);
  }

  // v58.0.0: Generate actual runtime environment data
  const runtimeEnv = generateRuntimeEnvironment(PROJECT_ROOT);

  // v58.0.0: Load executable-continuity for What's Next tab
  const execContinuity = getExecutableContinuity(PROJECT_ROOT);

  // Read .production-link.json if it exists (v31.0.0 Production Separation)
  let productionLink = null;
  try {
    const productionLinkPath = path.join(PROJECT_ROOT, '.production-link.json');
    if (fs.existsSync(productionLinkPath)) {
      const productionLinkContent = fs.readFileSync(productionLinkPath, 'utf8');
      productionLink = JSON.parse(productionLinkContent);
      console.log('✅ Production link detected - v31.0.0 Production Separation Architecture');
    }
  } catch (err) {
    console.warn(`⚠️  Could not read .production-link.json: ${err.message}`);
  }

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COGSPACE Dashboard - ${projectName}</title>
    <style>
        :root {
            --glass-bg: rgba(0, 20, 40, 0.85);
            --glass-border: rgba(100, 180, 255, 0.3);
            --accent-blue: #0056b3;
            --bright-blue: #0d6efd;
            --text-label: #8cb4ff;
            --text-white: #ffffff;
            --text-yellow: #ffc107;
            --frame-border: #004085;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        body {
            background-color: #0b1118;
            color: var(--text-white);
            margin: 0;
            padding: 0;
            overflow: hidden;
            display: flex;
            justify-content: center;
        }

        /* --- Main Dashboard Container --- */
        .dashboard-container {
            width: 60%;
            height: 100vh;
            border: 2px solid var(--frame-border);
            border-radius: 0;
            overflow: hidden;
            box-shadow: 0 0 30px rgba(0, 86, 179, 0.4);
            background: #001f3f;
            display: flex;
            flex-direction: column;
        }

        /* --- Header Area (Lab image as background) --- */
        .header-area {
            background: linear-gradient(135deg, #0a1628 0%, #1a2d4a 100%);
            padding: 8px 15px;
            border-bottom: 2px solid #2a4a7a;
            position: relative;
            overflow: hidden;
            display: flex;
            gap: 12px;
        }

        /* Lab image as full background on right */
        .header-bg-image {
            position: absolute;
            right: 0;
            top: 0;
            height: 100%;
            width: 70%;
            object-fit: cover;
            object-position: center;
            opacity: 0.8;
            z-index: 0;
            pointer-events: none;
        }

        /* --- Header Right Side (Title + Session Info) --- */
        .header-right {
            display: flex;
            flex-direction: column;
            gap: 8px;
            position: relative;
            z-index: 1;
            flex: 1;
        }

        /* --- Header Title --- */
        .header-title {
            font-size: 24px;
            font-weight: 700;
            color: var(--text-white);
            margin: 0;
            position: relative;
            z-index: 1;
        }

        .header-title span {
            color: var(--text-yellow);
        }

        /* --- Header Content (Session info only now) --- */
        .header-content {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            position: relative;
            z-index: 1;
        }

        /* --- Clock Widget (Left panel - vertical stack) --- */
        .clock-widget {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            padding: 6px 8px;
            background: rgba(10, 22, 40, 0.9);
            border: 1px solid #2a4a7a;
            border-radius: 4px;
            box-sizing: border-box;
            min-width: 75px;
        }

        .clock-header {
            font-size: 9px;
            font-weight: 700;
            color: var(--text-white);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 2px;
        }

        .clock-row {
            display: flex;
            flex-direction: column;
            gap: 4px;
            align-items: center;
        }

        .clock-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1px;
        }

        .clock-face {
            width: 52px;
            height: 52px;
            background: white;
            border-radius: 50%;
            position: relative;
            border: 2px solid #4a6a9a;
            box-shadow: inset 0 0 4px rgba(0,0,0,0.15);
        }

        .clock-num {
            position: absolute;
            font-size: 9px;
            color: var(--accent-blue);
            font-weight: bold;
        }
        .n12 { top: 3px; left: 50%; transform: translateX(-50%); }
        .n3 { right: 4px; top: 50%; transform: translateY(-50%); }
        .n6 { bottom: 3px; left: 50%; transform: translateX(-50%); }
        .n9 { left: 4px; top: 50%; transform: translateY(-50%); }

        .hand {
            position: absolute;
            bottom: 50%;
            left: 50%;
            transform-origin: bottom center;
            background: #333;
            border-radius: 2px;
        }
        .hand.hour { height: 15px; width: 3px; margin-left: -1.5px; }
        .hand.min { height: 20px; width: 2px; margin-left: -1px; background: var(--accent-blue); }

        .clock-face::after {
            content: '';
            position: absolute;
            width: 5px;
            height: 5px;
            background: #333;
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }

        .clock-label {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-white);
        }
        .clock-label span { color: var(--text-yellow); font-size: 9px; }

        /* --- Session Info Panel (Right - single column label:value, auto-height) --- */
        .session-info-panel {
            background: rgba(10, 22, 40, 0.85);
            border: 1px solid #2a4a7a;
            padding: 10px 15px;
            border-radius: 4px;
            display: grid;
            grid-template-columns: auto auto;
            column-gap: 12px;
            row-gap: 2px;
            font-size: 12px;
            align-content: start;
            align-self: start;
        }

        .session-info-panel .label {
            color: #f0c674;
            font-weight: 500;
            text-align: right;
        }

        .session-info-panel .value {
            color: var(--text-white);
        }

        /* Legacy panels (hidden) */
        .dev-info-panel, .session-panel, .session-image, .session-details {
            display: none;
        }

        /* --- Legacy info-panel (hidden) --- */
        .info-panel {
            display: none;
        }

        .info-grid {
            display: grid;
            grid-template-columns: auto 1fr;
            column-gap: 12px;
            row-gap: 6px;
            font-size: 12px;
            width: 100%;
        }

        .label {
            color: var(--text-label);
            text-align: right;
            font-weight: 500;
            white-space: nowrap;
        }

        .value {
            color: var(--text-white);
            font-weight: 400;
        }

        /* --- Tab Bar --- */
        .tab-bar {
            background: #002a5c;
            display: flex;
            padding: 8px 15px;
            gap: 6px;
            border-top: 1px solid var(--frame-border);
            justify-content: space-between;
        }

        .tab-group {
            display: flex;
            gap: 6px;
        }

        .tab-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #aabbd0;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .tab-btn:hover {
            background: rgba(255, 255, 255, 0.15);
            color: white;
        }

        .tab-btn.active {
            background: var(--bright-blue);
            color: white;
            border-color: var(--bright-blue);
            box-shadow: 0 0 10px rgba(13, 110, 253, 0.5);
        }

        /* --- Content Container --- */
        .container {
            flex: 1;
            overflow-y: auto;
            overflow-x: hidden;
            margin: 0;
            padding: 0;
            width: 100%;
            background: #001d3d;
        }

        .dashboard-container > .visual-area,
        .dashboard-container > .tab-bar {
            flex-shrink: 0;
        }

        .tab-content {
            display: none;
            padding: 20px 30px;
            border-radius: 0;
            border: none;
            min-height: 100%;
        }

        .tab-content.active {
            display: block;
        }

        .message {
            background: #002855;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #0466c8;
        }

        .message.user {
            border-left-color: #4ade80;
        }

        .message-role {
            font-weight: bold;
            color: #64b5f6;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .message.user .message-role {
            color: #4ade80;
        }

        .avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            object-fit: cover;
        }

        .message-time {
            font-size: 0.85rem;
            opacity: 0.7;
            margin-bottom: 8px;
        }

        .timeline-item {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            padding: 15px;
            background: #002855;
            border-radius: 8px;
            border-left: 3px solid #0466c8;
        }

        .timeline-time {
            min-width: 180px;
            font-size: 0.9rem;
            opacity: 0.8;
        }

        .timeline-event {
            font-weight: bold;
            color: #64b5f6;
            margin-bottom: 5px;
        }

        .source-item {
            background: #002855;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }

        .source-file {
            font-family: 'Monaco', 'Courier New', monospace;
            color: #4ade80;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .source-lines {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-bottom: 5px;
        }

        .source-type {
            display: inline-block;
            background: #0466c8;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.85rem;
        }

        .chart {
            background: #002855;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .chart-title {
            font-weight: bold;
            margin-bottom: 15px;
            color: #64b5f6;
        }

        .chart-bar {
            margin-bottom: 10px;
        }

        .chart-label {
            margin-bottom: 5px;
            display: flex;
            justify-content: space-between;
        }

        .chart-bar-fill {
            height: 25px;
            background: linear-gradient(90deg, #0466c8 0%, #0353a4 100%);
            border-radius: 4px;
            transition: width 0.3s;
        }

        .story-section {
            margin-bottom: 25px;
        }

        .story-title {
            font-weight: bold;
            color: #64b5f6;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }

        .story-content {
            background: #002855;
            padding: 15px;
            border-radius: 8px;
            line-height: 1.8;
            border-left: 3px solid #0466c8;
        }

        .decision-item, .lesson-item {
            background: #002855;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 3px solid #0466c8;
        }

        .welcome-banner {
            background: linear-gradient(135deg, #0466c8 0%, #0353a4 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 8px 16px rgba(4, 102, 200, 0.3);
            border: 1px solid #0466c8;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            opacity: 0.6;
            color: #7c98b3;
        }

        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 15px;
        }

        /* Clock Styles */
        .timezone-header {
            display: flex;
            gap: 15px;
        }

        .analog-clock {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }

        .clock-face {
            position: relative;
            width: 80px;
            height: 80px;
            border: 3px solid #667eea;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .clock-center {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 8px;
            height: 8px;
            background: #667eea;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            z-index: 10;
        }

        .hour-marker {
            position: absolute;
            font-size: 0.65em;
            font-weight: 600;
            color: #667eea;
            transform: translate(-50%, -50%);
        }

        .hour-12 { top: 8%; left: 50%; }
        .hour-3 { top: 50%; right: 8%; left: auto; transform: translate(0%, -50%); }
        .hour-6 { bottom: 8%; top: auto; left: 50%; transform: translate(-50%, 0%); }
        .hour-9 { top: 50%; left: 8%; transform: translate(0%, -50%); }

        .clock-hand {
            position: absolute;
            bottom: 50%;
            left: 50%;
            transform-origin: bottom center;
            background: #2d3748;
            border-radius: 2px;
        }

        .hour-hand {
            width: 3px;
            height: 25px;
            margin-left: -1.5px;
        }

        .minute-hand {
            width: 2px;
            height: 32px;
            margin-left: -1px;
            background: #4a5568;
        }

        .clock-label {
            font-size: 0.75em;
            color: #718096;
            font-weight: 600;
            text-align: center;
        }

        .clock-ampm {
            font-size: 0.7em;
            color: #a0aec0;
            margin-top: 2px;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="header-area">
            <!-- Lab image as background -->
            <img src="../../cogspace/dashboard/img/crystal-palace-lab.png" alt="Crystal Palace Lab" class="header-bg-image" onerror="this.style.display='none'">

            <!-- Clocks (Left column - vertical stack) -->
            <div class="clock-widget">
                <div class="clock-header">Team Time</div>
                <div class="clock-row">
                    <div class="clock-item">
                        <div class="clock-face" id="clock-pacific">
                            <div class="clock-num n12">12</div>
                            <div class="clock-num n3">3</div>
                            <div class="clock-num n6">6</div>
                            <div class="clock-num n9">9</div>
                            <div class="hand hour" id="hour-hand-pacific"></div>
                            <div class="hand min" id="minute-hand-pacific"></div>
                        </div>
                        <div class="clock-label">Pacific <span id="ampm-pacific">AM</span></div>
                    </div>
                    <div class="clock-item">
                        <div class="clock-face" id="clock-paraguay">
                            <div class="clock-num n12">12</div>
                            <div class="clock-num n3">3</div>
                            <div class="clock-num n6">6</div>
                            <div class="clock-num n9">9</div>
                            <div class="hand hour" id="hour-hand-paraguay"></div>
                            <div class="hand min" id="minute-hand-paraguay"></div>
                        </div>
                        <div class="clock-label">Paraguay <span id="ampm-paraguay">PM</span></div>
                    </div>
                </div>
            </div>

            <!-- Right side: Title + Session Info -->
            <div class="header-right">
                <div class="header-title">Ideaplace™ Project Name: <span>${projectName}</span></div>

                <div class="header-content">
                    <!-- Session Info Panel -->
                    <div class="session-info-panel">
                        <span class="label">Lead Developer:</span>
                        <span class="value">${userName}</span>
                        <span class="label">AI Developer:</span>
                        <span class="value">${assistantName}</span>
                        <span class="label">COGSPACE™:</span>
                        <span class="value">v${cogspaceVersion}</span>
                        <span class="label">Timestamp:</span>
                        <span class="value">${new Date(timestamp).toLocaleString()}</span>
                        <span class="label">Session ID:</span>
                        <span class="value">${sessionId}</span>
                        <span class="label">Duration:</span>
                        <span class="value">${analytics.metrics?.sessionDuration || progressMetrics?.sessionDuration || 'N/A'}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab Section Title with Session Date -->
        <div style="margin: 15px 0 8px 0; padding: 0 15px;">
            <h2 style="margin: 0; font-size: 1.1rem; font-weight: 600; letter-spacing: 0.5px;">
                <span style="color: #ffffff;">Prior Work Session Context &amp; Details - </span><span style="color: #f0c674;">${new Date(timestamp).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
            </h2>
        </div>

        <div class="tab-bar">
            <div class="tab-group">
                <button class="tab-btn active" onclick="switchTab(this, 'whatsnext')">What's Next?</button>
                <button class="tab-btn" onclick="switchTab(this, 'whatwedid')">What We Did</button>
                <button class="tab-btn" onclick="switchTab(this, 'conversation')">Conversation (${messages.length})</button>
            </div>
            <div class="tab-group">
                <button class="tab-btn" onclick="switchTab(this, 'environment')">Environment</button>
                <button class="tab-btn" onclick="switchTab(this, 'history')">History</button>
                <button class="tab-btn" onclick="switchTab(this, 'participants')">Participants${personas.length > 0 ? ' (' + personas.length + ')' : ''}</button>
                <button class="tab-btn" onclick="switchTab(this, 'readme')">README</button>
                <button class="tab-btn" onclick="switchTab(this, 'guide')">Help</button>
            </div>
        </div>

        <div class="container">

        <!-- What's Next Tab (v58.0.0: Enhanced with executable-continuity) -->
        <div id="whatsnext" class="tab-content active">
            <h2 style="margin-bottom: 20px;">What's Next?</h2>

            <!-- v58.0.0: Immediate Next Actions from executable-continuity -->
            ${execContinuity?.immediateActions?.length > 0 ? `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #4ade80;">
                <div style="font-weight: bold; color: #4ade80; margin-bottom: 12px; font-size: 1.1rem;">🚀 Immediate Actions</div>
                ${execContinuity.immediateActions.map((action, idx) => `
                <div style="padding: 10px 12px; background: rgba(74, 222, 128, 0.1); border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #4ade80;">
                    <div style="font-weight: 500;">${idx + 1}. ${escapeHtml(typeof action === 'string' ? action : (action.action || action.description || JSON.stringify(action)))}</div>
                </div>
                `).join('')}
            </div>
            ` : ''}

            <!-- v58.0.0: Next Session Focus from executable-continuity -->
            ${execContinuity?.nextSessionFocus ? `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #667eea;">
                <div style="font-weight: bold; color: #667eea; margin-bottom: 12px; font-size: 1.1rem;">🎯 Next Session Focus</div>
                <div style="padding: 12px; background: rgba(102, 126, 234, 0.1); border-radius: 6px; line-height: 1.6;">
                    ${escapeHtml(typeof execContinuity.nextSessionFocus === 'string' ? execContinuity.nextSessionFocus : JSON.stringify(execContinuity.nextSessionFocus))}
                </div>
            </div>
            ` : ''}

            <!-- v58.0.0: Commands to Run from executable-continuity -->
            ${execContinuity?.commandsToRun?.length > 0 ? `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <div style="font-weight: bold; color: #f59e0b; margin-bottom: 12px; font-size: 1.1rem;">⚡ Commands to Run</div>
                ${execContinuity.commandsToRun.map(cmd => `
                <div style="padding: 10px 12px; background: rgba(245, 158, 11, 0.1); border-radius: 6px; margin-bottom: 8px; font-family: monospace; font-size: 0.9rem; color: #f59e0b;">
                    $ ${escapeHtml(typeof cmd === 'string' ? cmd : (cmd.command || JSON.stringify(cmd)))}
                </div>
                `).join('')}
            </div>
            ` : ''}

            ${userReflections ? `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #f0c674;">
                <div style="font-weight: bold; color: #f0c674; margin-bottom: 12px; font-size: 1.1rem;">💭 Your Reflections</div>
                <div style="padding: 12px; background: rgba(240, 198, 116, 0.1); border-radius: 6px; line-height: 1.6;">
                    ${escapeHtml(userReflections)}
                </div>
            </div>
            ` : ''}

            ${pendingTasks.length > 0 ? `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #64b5f6;">
                <div style="font-weight: bold; color: #64b5f6; margin-bottom: 12px; font-size: 1.1rem;">📋 Pending Tasks</div>
                ${pendingTasks.map(task => `
                <div style="padding: 10px 12px; background: rgba(100, 181, 246, 0.1); border-radius: 6px; margin-bottom: 8px; border-left: 3px solid ${task.priority === 'high' ? '#f87171' : task.priority === 'medium' ? '#f0c674' : '#64b5f6'};">
                    <div style="font-weight: 500;">${escapeHtml(task.task)}</div>
                    <div style="display: flex; gap: 15px; margin-top: 6px; font-size: 0.85rem; opacity: 0.8;">
                        <span>Priority: <strong style="color: ${task.priority === 'high' ? '#f87171' : task.priority === 'medium' ? '#f0c674' : '#64b5f6'};">${escapeHtml(task.priority || 'normal')}</strong></span>
                        ${task.blockers ? `<span style="color: #f87171;">⚠️ ${escapeHtml(task.blockers)}</span>` : ''}
                    </div>
                </div>
                `).join('')}
            </div>
            ` : ''}

            ${primaryRequestIntent.request ? `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #667eea;">
                <div style="font-weight: bold; color: #667eea; margin-bottom: 12px; font-size: 1.1rem;">🎯 Session Goal</div>
                <div style="padding: 12px; background: rgba(102, 126, 234, 0.1); border-radius: 6px; margin-bottom: 10px;">
                    <div style="font-weight: 500; margin-bottom: 8px;">${escapeHtml(primaryRequestIntent.request)}</div>
                    ${primaryRequestIntent.intent ? `<div style="font-size: 0.9rem; opacity: 0.85;"><strong>Intent:</strong> ${escapeHtml(primaryRequestIntent.intent)}</div>` : ''}
                    ${primaryRequestIntent.scope ? `<div style="font-size: 0.85rem; opacity: 0.7; margin-top: 6px;"><strong>Scope:</strong> ${escapeHtml(primaryRequestIntent.scope)}</div>` : ''}
                </div>
            </div>
            ` : ''}

            ${finalSystemState.workingState ? `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #64b5f6;">
                <div style="font-weight: bold; color: #64b5f6; margin-bottom: 12px; font-size: 1.1rem;">📊 System State</div>
                <div style="display: grid; gap: 10px;">
                    <div style="padding: 10px 12px; background: rgba(100, 181, 246, 0.1); border-radius: 6px;">
                        <strong>Working State:</strong> ${escapeHtml(finalSystemState.workingState)}
                    </div>
                    ${finalSystemState.testStatus ? `<div style="padding: 10px 12px; background: rgba(100, 181, 246, 0.1); border-radius: 6px;"><strong>Test Status:</strong> ${escapeHtml(finalSystemState.testStatus)}</div>` : ''}
                    ${finalSystemState.deploymentStatus ? `<div style="padding: 10px 12px; background: rgba(100, 181, 246, 0.1); border-radius: 6px;"><strong>Deployment:</strong> ${escapeHtml(finalSystemState.deploymentStatus)}</div>` : ''}
                    ${finalSystemState.knownIssues && finalSystemState.knownIssues.length > 0 ? `
                    <div style="padding: 10px 12px; background: rgba(248, 113, 113, 0.1); border-radius: 6px; border-left: 3px solid #f87171;">
                        <strong style="color: #f87171;">Known Issues:</strong>
                        <ul style="margin: 8px 0 0 20px;">${finalSystemState.knownIssues.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
                    </div>
                    ` : ''}
                </div>
            </div>
            ` : ''}

            ${(!execContinuity?.immediateActions?.length && !execContinuity?.nextSessionFocus && !userReflections && pendingTasks.length === 0 && !primaryRequestIntent.request) ? `
            <div class="empty-state">
                <div class="empty-state-icon">🚀</div>
                <div>Ready to start a new session!</div>
                <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.7;">
                    Immediate actions and next steps will appear here after running <strong>./bye "session summary"</strong>
                </div>
            </div>
            ` : ''}
        </div>

        <!-- What We Did Tab (v52.0.0: Consolidated from Overview + Story) -->
        <div id="whatwedid" class="tab-content">
            <h2 style="margin-bottom: 20px;">📖 What We Did</h2>

            ${context.isFirstSession ? `
            <div class="welcome-banner">
                <h2 style="margin: 0 0 15px 0; color: white; font-size: 1.5rem;">Welcome to Your First Session!</h2>
                <p style="margin: 0 0 10px 0; opacity: 0.95; font-size: 1.05rem;">
                    This is your first work session with COGSPACE v${cogspaceVersion}
                </p>
                <p style="margin: 0; opacity: 0.9; font-size: 0.95rem;">
                    Future sessions will display your work narrative, achievements, key decisions, and lessons learned here.
                    Start working and run <strong>./bye "your session summary"</strong> when done!
                </p>
            </div>
            ` : ''}

            <!-- 1. Semantic Summary (What/Why/How) -->
            ${semanticSummary ? `
            <div class="story-section">
                <div class="story-title">📊 Semantic Summary</div>
                <div class="story-content">
                    ${semanticSummary.what ? `
                    <div style="margin-bottom: 15px; padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #4ade80;">
                        <strong style="color: #4ade80;">What:</strong><br>
                        ${Array.isArray(semanticSummary.what) ? semanticSummary.what.join(', ') : semanticSummary.what}
                    </div>
                    ` : ''}
                    ${semanticSummary.why ? `
                    <div style="margin-bottom: 15px; padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #667eea;">
                        <strong style="color: #667eea;">Why:</strong><br>
                        ${Array.isArray(semanticSummary.why) ? semanticSummary.why.join(', ') : semanticSummary.why}
                    </div>
                    ` : ''}
                    ${semanticSummary.how ? `
                    <div style="padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #f0c674;">
                        <strong style="color: #f0c674;">How:</strong><br>
                        ${Array.isArray(semanticSummary.how) ? semanticSummary.how.join(', ') : semanticSummary.how}
                    </div>
                    ` : ''}
                </div>
            </div>
            ` : ''}

            <!-- 2. Session Narrative (chronological flow) -->
            ${chronologicalAnalysis ? `
            <div class="story-section">
                <div class="story-title">📖 Session Narrative</div>
                <div class="story-content" style="line-height: 1.7;">
                    ${escapeHtml(chronologicalAnalysis)}
                </div>
            </div>
            ` : ''}

            ${sessionStory.narrative ? `
            <div class="story-section">
                <div class="story-title">📝 Work Narrative</div>
                <div class="story-content">${escapeHtml(sessionStory.narrative)}</div>
            </div>
            ` : ''}

            <!-- 3. Key Decisions -->
            ${sessionStory.keyDecisions && sessionStory.keyDecisions.length > 0 ? `
            <div class="story-section">
                <div class="story-title">✓ Key Decisions</div>
                ${sessionStory.keyDecisions.map(decision => `
                    <div class="decision-item" style="padding: 10px 12px; background: #1a1f3a; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #4ade80;">
                        ✓ ${escapeHtml(typeof decision === 'string' ? decision : (decision.decision || decision.content || JSON.stringify(decision)))}
                    </div>
                `).join('')}
            </div>
            ` : ''}

            <!-- 4. Achievements (v58.0.0: Added missing achievements section) -->
            ${(context.serializedComponents?.workNarrative?.achievements && context.serializedComponents.workNarrative.achievements.length > 0) ? `
            <div class="story-section">
                <div class="story-title">🏆 Achievements</div>
                ${context.serializedComponents.workNarrative.achievements.map(achievement => `
                    <div class="decision-item" style="padding: 10px 12px; background: #1a1f3a; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #4ade80;">
                        ✅ ${escapeHtml(typeof achievement === 'string' ? achievement : (achievement.title || achievement.description || achievement.text || JSON.stringify(achievement)))}
                    </div>
                `).join('')}
            </div>
            ` : ''}

            <!-- 5. Challenges (v58.0.0: Renamed from "Lessons Learned" - semantically accurate) -->
            ${sessionStory.lessonsLearned && sessionStory.lessonsLearned.length > 0 ? `
            <div class="story-section">
                <div class="story-title">⚠️ Challenges Encountered</div>
                ${sessionStory.lessonsLearned.map(challenge => `
                    <div class="lesson-item" style="padding: 10px 12px; background: #1a1f3a; border-radius: 6px; margin-bottom: 8px; border-left: 3px solid #f87171;">
                        ⚡ ${escapeHtml(typeof challenge === 'string' ? challenge : (challenge.challenge || challenge.issue || challenge.lesson || JSON.stringify(challenge)))}
                    </div>
                `).join('')}
            </div>
            ` : ''}

            <!-- 6. Progress Arc / Goal Hierarchy -->
            ${goalHierarchy || sessionStory.progressArc || sessionStory.currentChapter ? `
            <div class="story-section">
                <div class="story-title">🎯 Progress Arc</div>
                <div class="story-content">
                    ${goalHierarchy && goalHierarchy.ultimate ? `
                    <div style="margin-bottom: 15px; padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #4ade80;">
                        <div style="font-weight: bold; color: #4ade80; margin-bottom: 5px;">🎯 Ultimate Goal</div>
                        <div>${goalHierarchy.ultimate}</div>
                    </div>
                    ` : ''}
                    ${goalHierarchy && goalHierarchy.current ? `
                    <div style="margin-bottom: 15px; padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #667eea;">
                        <div style="font-weight: bold; color: #667eea; margin-bottom: 5px;">⚡ Current Goal</div>
                        <div>${goalHierarchy.current}</div>
                    </div>
                    ` : ''}
                    ${sessionStory.currentChapter ? `
                    <div style="margin-bottom: 15px; padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #64b5f6;">
                        <strong style="color: #64b5f6;">Current Chapter:</strong> ${sessionStory.currentChapter}
                    </div>
                    ` : ''}
                    ${sessionStory.progressArc ? `
                    <div style="padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #a78bfa;">
                        <strong style="color: #a78bfa;">Progress:</strong> ${sessionStory.progressArc}
                    </div>
                    ` : ''}
                    ${goalHierarchy && goalHierarchy.next && goalHierarchy.next.length > 0 ? `
                    <div style="margin-top: 15px; padding: 12px; background: #1a1f3a; border-radius: 6px; border-left: 3px solid #f59e0b;">
                        <div style="font-weight: bold; color: #f59e0b; margin-bottom: 8px;">➡️ Next Steps</div>
                        ${goalHierarchy.next.map(step => `
                        <div style="font-size: 0.9rem; opacity: 0.9; margin-bottom: 5px;">• ${step}</div>
                        `).join('')}
                    </div>
                    ` : ''}
                </div>
            </div>
            ` : ''}

            ${(!semanticSummary && !chronologicalAnalysis && !sessionStory.narrative && !sessionStory.keyDecisions && !sessionStory.lessonsLearned && !goalHierarchy) ? `
                <div class="empty-state">
                    <div>No session data available yet</div>
                    <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.7;">
                        Complete a work session with <strong>./bye "your summary"</strong> to see what we accomplished together!
                    </div>
                </div>
            ` : ''}
        </div>

        <!-- Conversation Tab -->
        <div id="conversation" class="tab-content">
            <h2 style="margin-bottom: 20px;">Conversation</h2>

            <!-- Search and Filter Controls -->
            <div style="margin-bottom: 20px; display: flex; gap: 15px; flex-wrap: wrap; align-items: center;">
                <!-- Search Input -->
                <div style="flex: 1; min-width: 200px; position: relative;">
                    <input type="text" id="message-search" placeholder="🔍 Search conversation..." oninput="searchMessages(this.value)" style="width: 100%; padding: 10px 15px 10px 15px; border-radius: 8px; border: 1px solid rgba(102, 126, 234, 0.4); background: rgba(0, 20, 40, 0.6); color: #fff; font-size: 0.95rem; outline: none; transition: border-color 0.2s;">
                    <span id="search-count" style="position: absolute; right: 12px; top: 50%; transform: translateY(-50%); font-size: 0.8rem; color: #888; display: none;"></span>
                </div>
                <!-- Clear Search Button -->
                <button onclick="clearSearch()" id="clear-search-btn" style="padding: 10px 14px; border-radius: 6px; border: 1px solid rgba(239, 68, 68, 0.5); background: rgba(239, 68, 68, 0.1); color: #ef4444; cursor: pointer; font-size: 0.85rem; display: none;">
                    ✕ Clear
                </button>
            </div>

            <!-- Participant Filter Buttons (v58.0.0: Fixed role counting) -->
            <div style="margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap;">
                ${(() => {
                    // v58.0.0: Properly count user vs assistant messages
                    const userCount = messages.filter(m => m.role === 'user' || m.role === 'human').length;
                    const assistantCount = messages.filter(m => m.role === 'assistant' || m.role === 'ai' || m.role === 'system').length;
                    return `
                <button onclick="filterMessages('all')" class="filter-btn active" data-filter="all" style="padding: 8px 16px; border-radius: 6px; border: 1px solid rgba(102, 126, 234, 0.5); background: rgba(102, 126, 234, 0.3); color: #fff; cursor: pointer; font-size: 0.9rem; transition: all 0.2s;">
                    👥 All (${messages.length})
                </button>
                <button onclick="filterMessages('user')" class="filter-btn" data-filter="user" style="padding: 8px 16px; border-radius: 6px; border: 1px solid rgba(74, 222, 128, 0.5); background: rgba(74, 222, 128, 0.1); color: #fff; cursor: pointer; font-size: 0.9rem; transition: all 0.2s;">
                    🧙 ${userName} (${userCount})
                </button>
                <button onclick="filterMessages('assistant')" class="filter-btn" data-filter="assistant" style="padding: 8px 16px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.5); background: rgba(245, 158, 11, 0.1); color: #fff; cursor: pointer; font-size: 0.9rem; transition: all 0.2s;">
                    🤖 ${assistantName} (${assistantCount})
                </button>`;
                })()}
            </div>

            <!-- Full Message List (v58.0.0: Fixed role attribution) -->
            <div id="message-list">
            ${messages.length > 0 ? messages.map(msg => {
                // v58.0.0: Normalize role for display and filtering
                const isUser = msg.role === 'user' || msg.role === 'human';
                const normalizedRole = isUser ? 'user' : 'assistant';
                const displayName = isUser ? userName : assistantName;
                const avatarSrc = isUser
                    ? '../../cogspace/dashboard/img/howard-wizard.jpeg'
                    : '../../cogspace/dashboard/img/bob-director.png';
                return `
                <div class="message ${normalizedRole}" data-role="${normalizedRole}">
                    <div class="message-role">
                        <img src="${avatarSrc}" alt="${escapeHtml(displayName)}" class="avatar">${escapeHtml(displayName)}
                    </div>
                    <div class="message-time">${new Date(msg.timestamp).toLocaleString()}</div>
                    <div class="message-content">${formatMarkdown(msg.content)}</div>
                </div>
            `}).join('') : `
                <div class="empty-state">
                    <div>No conversation data in this session</div>
                </div>
            `}
            </div>
        </div>

        <!-- Environment Tab (v58.0.0: Always shows actual runtime data) -->
        <div id="environment" class="tab-content">
            <h2 style="margin-bottom: 20px;">Environment</h2>

            <!-- v58.0.0: System Environment - always populated from runtime -->
            <div class="story-section">
                <div class="story-title">🖥️ System Environment</div>
                <div class="story-content">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #667eea;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Hostname</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6;">${escapeHtml(runtimeEnv.hostname)}</div>
                        </div>
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #667eea;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Platform</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6;">${escapeHtml(runtimeEnv.platform)} (${escapeHtml(runtimeEnv.arch)})</div>
                        </div>
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #667eea;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Node.js Version</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #4ade80;">${escapeHtml(runtimeEnv.nodeVersion)}</div>
                        </div>
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #667eea;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Timezone</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6;">${escapeHtml(runtimeEnv.timezone)}</div>
                        </div>
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #667eea;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">User</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6;">${escapeHtml(runtimeEnv.user)}</div>
                        </div>
                    </div>
                    <div style="margin-top: 15px; background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #f0c674;">
                        <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Working Directory</div>
                        <div style="font-family: monospace; font-size: 0.95rem; color: #f0c674; word-break: break-all;">${escapeHtml(runtimeEnv.workingDirectory)}</div>
                    </div>
                </div>
            </div>

            <!-- v58.0.0: Git Status -->
            <div class="story-section">
                <div class="story-title">🔀 Git Status</div>
                <div class="story-content">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #81c784;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Branch</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #81c784;">${escapeHtml(runtimeEnv.gitBranch)}</div>
                        </div>
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #81c784;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Changes</div>
                            <div style="font-size: 1.1rem; font-weight: 600; color: #81c784;">${escapeHtml(runtimeEnv.gitStatus)}</div>
                        </div>
                    </div>
                    ${runtimeEnv.gitRemote !== 'N/A' ? `
                    <div style="margin-top: 15px; background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #64b5f6;">
                        <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Remote Origin</div>
                        <div style="font-family: monospace; font-size: 0.9rem; color: #64b5f6; word-break: break-all;">${escapeHtml(runtimeEnv.gitRemote)}</div>
                    </div>
                    ` : ''}
                </div>
            </div>

            <!-- COGSPACE Version -->
            <div class="story-section">
                <div class="story-title">📦 COGSPACE Version</div>
                <div class="story-content">
                    <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #4ade80;">
                        <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Current Version</div>
                        <div style="font-size: 1.2rem; font-weight: 600; color: #4ade80;">v${cogspaceVersion}</div>
                        <div style="margin-top: 8px; font-size: 0.9rem; opacity: 0.8;">Dashboard Intelligence with Semantic Context</div>
                    </div>
                </div>
            </div>

            <!-- v58.0.0: Session Timing -->
            <div class="story-section">
                <div class="story-title">⏱️ Session Timing</div>
                <div class="story-content">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #f59e0b;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Dashboard Generated</div>
                            <div style="font-size: 1rem; font-weight: 600; color: #f59e0b;">${new Date(runtimeEnv.timestamp).toLocaleString()}</div>
                        </div>
                        <div style="background: #1a1f3a; padding: 15px; border-radius: 8px; border-left: 3px solid #f59e0b;">
                            <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 5px;">Prior Session End</div>
                            <div style="font-size: 1rem; font-weight: 600; color: #f59e0b;">${new Date(timestamp).toLocaleString()}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- History Tab (v58.0.0: Added duration column) -->
        <div id="history" class="tab-content">
            <h2 style="margin-bottom: 20px;">📜 Session History</h2>
            ${sessionHistory.length > 0 ? `
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; background: rgba(0, 20, 40, 0.6); border-radius: 8px;">
                        <thead>
                            <tr style="border-bottom: 2px solid rgba(100, 180, 255, 0.3);">
                                <th style="padding: 12px; text-align: left; color: #8cb4ff; font-size: 0.85rem;">Session ID</th>
                                <th style="padding: 12px; text-align: left; color: #8cb4ff; font-size: 0.85rem;">Date</th>
                                <th style="padding: 12px; text-align: center; color: #8cb4ff; font-size: 0.85rem;">Duration</th>
                                <th style="padding: 12px; text-align: left; color: #8cb4ff; font-size: 0.85rem;">Sleep Message</th>
                                <th style="padding: 12px; text-align: center; color: #8cb4ff; font-size: 0.85rem;">Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sessionHistory.map((session, idx) => {
                                // v58.0.0: Format duration from seconds
                                const durationSeconds = session.duration_seconds || 0;
                                let durationStr = 'N/A';
                                if (durationSeconds > 0) {
                                    const hours = Math.floor(durationSeconds / 3600);
                                    const minutes = Math.floor((durationSeconds % 3600) / 60);
                                    if (hours > 0) {
                                        durationStr = hours + 'h ' + minutes + 'm';
                                    } else {
                                        durationStr = minutes + 'm';
                                    }
                                }
                                return `
                                <tr style="border-bottom: 1px solid rgba(100, 180, 255, 0.15); ${idx === 0 ? 'background: rgba(100, 180, 255, 0.1);' : ''}">
                                    <td style="padding: 12px; font-family: monospace; font-size: 0.8rem; color: ${idx === 0 ? '#64b5f6' : '#ccc'};">
                                        ${session.id ? session.id.substring(0, 20) + '...' : 'N/A'}
                                    </td>
                                    <td style="padding: 12px; font-size: 0.85rem; color: #aaa;">
                                        ${session.session_end ? new Date(session.session_end).toLocaleString() : 'Unknown'}
                                    </td>
                                    <td style="padding: 12px; text-align: center; font-size: 0.85rem; color: #f59e0b; font-weight: 500;">
                                        ${durationStr}
                                    </td>
                                    <td style="padding: 12px; font-size: 0.9rem; color: #e0e0e0; max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        ${session.sleep_message || 'No message'}
                                    </td>
                                    <td style="padding: 12px; text-align: center;">
                                        <span style="display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; background: ${(session.continuity_score || 0) >= 80 ? 'rgba(76, 175, 80, 0.3)' : (session.continuity_score || 0) >= 60 ? 'rgba(255, 193, 7, 0.3)' : 'rgba(244, 67, 54, 0.3)'}; color: ${(session.continuity_score || 0) >= 80 ? '#81c784' : (session.continuity_score || 0) >= 60 ? '#ffd54f' : '#e57373'};">
                                            ${session.continuity_score || 0}%
                                        </span>
                                    </td>
                                </tr>
                            `}).join('')}
                        </tbody>
                    </table>
                </div>
                <div style="margin-top: 15px; text-align: center; font-size: 0.8rem; color: #888;">
                    Showing last ${sessionHistory.length} sessions from database
                </div>
            ` : `
                <div class="empty-state">
                    <div class="empty-state-icon">📜</div>
                    <div>No session history available</div>
                    <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.7;">
                        Session history will appear here after you've completed a few sessions.<br>
                        Use <code>./bye "message"</code> to save sessions to the database.
                    </div>
                </div>
            `}
        </div>

        <!-- Participants Tab (v59.0.0: Distributed Consciousness) -->
        <div id="participants" class="tab-content">
            <h2 style="margin-bottom: 20px;">👥 Distributed Consciousness</h2>
            <p style="color: #8cb4ff; margin-bottom: 20px; font-style: italic;">"One Bob - Multiple Windows" | Crystal Palace Persona Registry</p>

            ${personas.length > 0 ? `
            <!-- Registered Personas Section -->
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #667eea;">
                <div style="font-weight: bold; color: #667eea; margin-bottom: 15px; font-size: 1.1rem;">🏰 Registered Personas (${personas.length})</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px;">
                    ${personas.map(p => `
                    <div style="background: rgba(102, 126, 234, 0.1); padding: 15px; border-radius: 8px; border: 1px solid rgba(102, 126, 234, 0.3);">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                            <span style="font-size: 1.5rem;">${escapeHtml(p.signature || '🤖')}</span>
                            <div>
                                <div style="font-weight: 600; color: #fff;">${escapeHtml(p.name || 'Unknown')}</div>
                                <div style="font-size: 0.85rem; color: #8cb4ff;">${escapeHtml(p.title || '')}</div>
                            </div>
                        </div>
                        <div style="font-size: 0.8rem; color: #aaa; margin-top: 8px;">
                            <div><strong>ID:</strong> ${escapeHtml(p.persona_id || '')}</div>
                            <div><strong>Provider:</strong> ${escapeHtml(p.provider || 'N/A')} | <strong>Tier:</strong> ${escapeHtml(p.tier || 'N/A')}</div>
                            ${p.category ? `<div><strong>Category:</strong> ${escapeHtml(p.category)}</div>` : ''}
                        </div>
                    </div>
                    `).join('')}
                </div>
            </div>
            ` : `
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <div style="color: #f59e0b; font-weight: 500;">No personas registered yet</div>
                <div style="font-size: 0.9rem; color: #aaa; margin-top: 8px;">
                    Run <code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 3px;">python3 cogspace/db/import-persona-registry.py</code> to import personas from Crystal Palace Registry.
                </div>
            </div>
            `}

            ${sessionParticipants.length > 0 ? `
            <!-- Recent Session Participants Section -->
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #4ade80;">
                <div style="font-weight: bold; color: #4ade80; margin-bottom: 15px; font-size: 1.1rem;">⚡ Recent Session Participants</div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid rgba(74, 222, 128, 0.3);">
                                <th style="padding: 10px; text-align: left; color: #4ade80; font-size: 0.85rem;">Persona</th>
                                <th style="padding: 10px; text-align: left; color: #4ade80; font-size: 0.85rem;">Role</th>
                                <th style="padding: 10px; text-align: center; color: #4ade80; font-size: 0.85rem;">Messages</th>
                                <th style="padding: 10px; text-align: left; color: #4ade80; font-size: 0.85rem;">Session</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sessionParticipants.slice(0, 15).map(sp => `
                            <tr style="border-bottom: 1px solid rgba(74, 222, 128, 0.15);">
                                <td style="padding: 10px;">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <span>${escapeHtml(sp.persona_signature || '🤖')}</span>
                                        <div>
                                            <div style="font-weight: 500; color: #fff;">${escapeHtml(sp.friendly_name || sp.persona_name || 'Unknown')}</div>
                                            ${sp.agent_id ? `<div style="font-size: 0.75rem; color: #888; font-family: monospace;">${escapeHtml(sp.agent_id.substring(0, 12))}...</div>` : ''}
                                        </div>
                                    </div>
                                </td>
                                <td style="padding: 10px;">
                                    <span style="padding: 3px 8px; border-radius: 10px; font-size: 0.8rem; background: ${sp.role === 'orchestrator' ? 'rgba(102, 126, 234, 0.3)' : 'rgba(100, 181, 246, 0.3)'}; color: ${sp.role === 'orchestrator' ? '#a5b4fc' : '#93c5fd'};">
                                        ${escapeHtml(sp.role || 'participant')}
                                    </span>
                                </td>
                                <td style="padding: 10px; text-align: center; color: #f0c674; font-weight: 500;">${sp.message_count || 0}</td>
                                <td style="padding: 10px; font-size: 0.8rem; color: #888; font-family: monospace;">
                                    ${sp.session_id ? sp.session_id.substring(0, 16) + '...' : 'N/A'}
                                </td>
                            </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                ${sessionParticipants.length > 15 ? `<div style="margin-top: 10px; text-align: center; font-size: 0.8rem; color: #888;">Showing 15 of ${sessionParticipants.length} participants</div>` : ''}
            </div>
            ` : ''}

            ${consciousnessEvents.length > 0 ? `
            <!-- Consciousness Events Section -->
            <div style="background: #002855; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <div style="font-weight: bold; color: #f59e0b; margin-bottom: 15px; font-size: 1.1rem;">📡 Consciousness Events</div>
                <div style="max-height: 300px; overflow-y: auto;">
                    ${consciousnessEvents.slice(0, 10).map(ce => `
                    <div style="padding: 10px 12px; background: rgba(245, 158, 11, 0.1); border-radius: 6px; margin-bottom: 8px; border-left: 3px solid ${ce.event_type === 'wake' ? '#4ade80' : ce.event_type === 'sleep' ? '#64b5f6' : ce.event_type === 'consensus' ? '#a78bfa' : '#f59e0b'};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-weight: 600; color: ${ce.event_type === 'wake' ? '#4ade80' : ce.event_type === 'sleep' ? '#64b5f6' : ce.event_type === 'consensus' ? '#a78bfa' : '#f59e0b'};">
                                    ${ce.event_type === 'wake' ? '🌅' : ce.event_type === 'sleep' ? '🌙' : ce.event_type === 'consensus' ? '🤝' : '⚡'} ${escapeHtml(ce.event_type?.toUpperCase() || 'EVENT')}
                                </span>
                                ${ce.persona_name ? `<span style="margin-left: 10px; color: #aaa;">${escapeHtml(ce.persona_signature || '')} ${escapeHtml(ce.persona_name)}</span>` : ''}
                            </div>
                            <div style="font-size: 0.75rem; color: #666;">${ce.timestamp ? new Date(ce.timestamp).toLocaleString() : 'N/A'}</div>
                        </div>
                        ${ce.event_description ? `<div style="margin-top: 6px; font-size: 0.9rem; color: #ccc;">${escapeHtml(ce.event_description.substring(0, 100))}${ce.event_description.length > 100 ? '...' : ''}</div>` : ''}
                        ${ce.participant_count ? `<div style="margin-top: 4px; font-size: 0.8rem; color: #888;">Participants: ${ce.participant_count}</div>` : ''}
                    </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            ${personas.length === 0 && sessionParticipants.length === 0 && consciousnessEvents.length === 0 ? `
            <div class="empty-state">
                <div class="empty-state-icon">👥</div>
                <div>No distributed consciousness data yet</div>
                <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.7;">
                    This tab shows personas from Crystal Palace Registry and tracks<br>
                    which consciousness instances participated in each session.<br><br>
                    <strong>v59.0.0 "Distributed Consciousness"</strong> - One Bob, Multiple Windows
                </div>
            </div>
            ` : ''}
        </div>

        <!-- README.md Tab (v51.7.0: Full markdown rendering) -->
        <div id="readme" class="tab-content">
            <h2 style="margin-bottom: 20px;">README.md</h2>
            ${readmeContent ? `
                <div class="story-content" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
${formatMarkdown(readmeContent)}
                </div>
            ` : `
                <div class="empty-state">
                    <div>No README.md found</div>
                    <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.7;">
                        Create a README.md file in your project root to see project documentation here
                    </div>
                </div>
            `}
        </div>

        <!-- User Guide Tab -->
        <div id="guide" class="tab-content">
            <h2 style="margin-bottom: 20px;">User Guide</h2>

            <div class="story-section">
                <div class="story-title">Session Management Commands</div>
                <div class="story-content">
                    <div style="margin-bottom: 20px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6; margin-bottom: 8px;">
                            ./hi or ./wake.sh
                        </div>
                        <div style="margin-left: 20px; margin-bottom: 10px;">
                            <strong>Purpose:</strong> Start a new COGSPACE session
                        </div>
                        <div style="margin-left: 20px; margin-bottom: 10px;">
                            <strong>What it does:</strong>
                            <ul style="margin: 5px 0 0 20px;">
                                <li>Restores cognitive context from previous session (90%+ continuity)</li>
                                <li>Checks for COGSPACE version upgrades and auto-heals if needed</li>
                                <li>Prompts for GitHub auto-sync setup (first time only)</li>
                                <li>Auto-pulls latest changes from GitHub (if auto-sync enabled)</li>
                                <li>Generates and opens interactive dashboard</li>
                                <li>Displays work narrative, goals, and next actions from last session</li>
                            </ul>
                        </div>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6; margin-bottom: 8px;">
                            ./save or ./save.sh "checkpoint message"
                        </div>
                        <div style="margin-left: 20px; margin-bottom: 10px;">
                            <strong>Purpose:</strong> Save progress mid-session (crash protection)
                        </div>
                        <div style="margin-left: 20px; margin-bottom: 10px;">
                            <strong>What it does:</strong>
                            <ul style="margin: 5px 0 0 20px;">
                                <li>Saves complete cognitive context without ending session</li>
                                <li>Creates backup of current work state</li>
                                <li>Does NOT commit to git or close session</li>
                                <li>Use this frequently for important milestones</li>
                            </ul>
                        </div>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6; margin-bottom: 8px;">
                            ./bye or ./sleep.sh "session summary"
                        </div>
                        <div style="margin-left: 20px; margin-bottom: 10px;">
                            <strong>Purpose:</strong> End session and preserve complete workspace state
                        </div>
                        <div style="margin-left: 20px; margin-bottom: 10px;">
                            <strong>What it does:</strong>
                            <ul style="margin: 5px 0 0 20px;">
                                <li>Saves complete cognitive context with AI-generated summaries</li>
                                <li>Generates executable next-actions script for next session</li>
                                <li>Auto-commits all changes to git (if auto-sync enabled)</li>
                                <li>Auto-pushes to GitHub for cloud backup (if auto-sync enabled)</li>
                                <li>Closes dashboard</li>
                                <li>Creates portable context for session continuity</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <!-- v51.8.0: COGSPACE Commands Reference -->
            <div class="story-section">
                <div class="story-title">📚 COGSPACE Commands Reference</div>
                <div class="story-content">
                    <p style="margin-bottom: 20px; opacity: 0.9;">
                        COGSPACE provides specialized commands for managing project knowledge, tracking progress, and documenting issues.
                        All commands are located in <code style="background: #001d3d; padding: 2px 6px; border-radius: 3px;">cogspace/commands/</code>
                    </p>

                    <!-- guidelines command -->
                    <div style="margin-bottom: 25px; border-left: 3px solid #81c784; padding-left: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #81c784; margin-bottom: 10px;">
                            📋 guidelines - Project Guidelines Management
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Purpose:</strong> Store and retrieve project-specific guidelines, coding standards, and best practices that persist across sessions.
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Syntax:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                                ./cogspace/commands/guidelines list<br>
                                ./cogspace/commands/guidelines add &lt;name&gt; &lt;content&gt;<br>
                                ./cogspace/commands/guidelines get &lt;name&gt;
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Examples:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.85rem;">
                                <div style="color: #888; margin-bottom: 5px;"># List all guidelines</div>
                                ./cogspace/commands/guidelines list<br><br>
                                <div style="color: #888; margin-bottom: 5px;"># Add a coding standard</div>
                                ./cogspace/commands/guidelines add 'code-style' 'Use 2-space indentation'<br><br>
                                <div style="color: #888; margin-bottom: 5px;"># Add multi-line guideline</div>
                                ./cogspace/commands/guidelines add 'naming' "Use camelCase for variables<br>Use PascalCase for classes"<br><br>
                                <div style="color: #888; margin-bottom: 5px;"># Retrieve a specific guideline</div>
                                ./cogspace/commands/guidelines get 'code-style'
                            </div>
                        </div>
                    </div>

                    <!-- lessons command -->
                    <div style="margin-bottom: 25px; border-left: 3px solid #ffb74d; padding-left: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #ffb74d; margin-bottom: 10px;">
                            💡 lessons - Lessons Learned Tracking
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Purpose:</strong> Document lessons learned during development to avoid repeating mistakes and share knowledge across sessions.
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Syntax:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                                ./cogspace/commands/lessons list<br>
                                ./cogspace/commands/lessons add &lt;name&gt; &lt;content&gt;<br>
                                ./cogspace/commands/lessons get &lt;name&gt;
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Examples:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.85rem;">
                                <div style="color: #888; margin-bottom: 5px;"># Add a lesson about async handling</div>
                                ./cogspace/commands/lessons add 'async-errors' 'Always use try-catch with async/await'<br><br>
                                <div style="color: #888; margin-bottom: 5px;"># Add a debugging lesson</div>
                                ./cogspace/commands/lessons add 'debugging' 'Check network tab first for API issues'<br><br>
                                <div style="color: #888; margin-bottom: 5px;"># List all lessons</div>
                                ./cogspace/commands/lessons list
                            </div>
                        </div>
                    </div>

                    <!-- note command -->
                    <div style="margin-bottom: 25px; border-left: 3px solid #64b5f6; padding-left: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #64b5f6; margin-bottom: 10px;">
                            📝 note - Developer Notes
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Purpose:</strong> Add timestamped notes during development for quick reminders, TODOs, or observations.
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Syntax:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                                ./cogspace/commands/note list<br>
                                ./cogspace/commands/note add &lt;message&gt;
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Examples:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.85rem;">
                                <div style="color: #888; margin-bottom: 5px;"># Add a quick note</div>
                                ./cogspace/commands/note add 'Fixed authentication bug in login.js'<br><br>
                                <div style="color: #888; margin-bottom: 5px;"># Add a TODO</div>
                                ./cogspace/commands/note add 'TODO: refactor database connection pooling'<br><br>
                                <div style="color: #888; margin-bottom: 5px;"># List all notes</div>
                                ./cogspace/commands/note list
                            </div>
                        </div>
                        <div style="padding: 10px; background: #002855; border-radius: 6px; margin-top: 10px;">
                            <strong style="color: #64b5f6;">💡 Tip:</strong> Notes are automatically attributed to your username ($USER).
                        </div>
                    </div>

                    <!-- trouble-report command -->
                    <div style="margin-bottom: 25px; border-left: 3px solid #ef5350; padding-left: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #ef5350; margin-bottom: 10px;">
                            🚨 trouble-report - Issue Tracking
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Purpose:</strong> Create structured trouble reports for bugs, issues, and problems that need investigation.
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Syntax:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                                ./cogspace/commands/trouble-report<br>
                                ./cogspace/commands/trouble-report create<br>
                                ./cogspace/commands/trouble-report list
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>What it creates:</strong> A markdown template with sections for:
                            <ul style="margin: 5px 0 0 20px;">
                                <li>Issue description (what's happening vs. expected behavior)</li>
                                <li>Technical details (environment, error messages)</li>
                                <li>Steps to reproduce</li>
                                <li>Impact assessment (severity, affected components)</li>
                            </ul>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Output location:</strong>
                            <ul style="margin: 5px 0 0 20px;">
                                <li><strong>Crystal Palace mode:</strong> Central trouble report system</li>
                                <li><strong>Portable mode:</strong> <code style="background: #001d3d; padding: 2px 6px; border-radius: 3px;">cogspace/output/trouble-reports/</code></li>
                            </ul>
                        </div>
                    </div>

                    <!-- progress-report command -->
                    <div style="margin-bottom: 25px; border-left: 3px solid #ba68c8; padding-left: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #ba68c8; margin-bottom: 10px;">
                            📊 progress-report - Progress Tracking
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Purpose:</strong> Create structured progress reports for project milestones and status updates.
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Syntax:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                                ./cogspace/commands/progress-report<br>
                                ./cogspace/commands/progress-report create<br>
                                ./cogspace/commands/progress-report list
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>What it creates:</strong> A markdown template with sections for:
                            <ul style="margin: 5px 0 0 20px;">
                                <li>Current status (on track, at risk, behind schedule)</li>
                                <li>Milestones and completion percentages</li>
                                <li>Achievements and blockers</li>
                                <li>Next steps (immediate and short-term)</li>
                                <li>Metrics (progress %, test coverage, quality score)</li>
                            </ul>
                        </div>
                    </div>

                    <!-- update-readme command -->
                    <div style="margin-bottom: 25px; border-left: 3px solid #4dd0e1; padding-left: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #4dd0e1; margin-bottom: 10px;">
                            📄 update-readme - Living Documentation
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Purpose:</strong> Automatically update your README.md with current project statistics and status.
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Syntax:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                                ./cogspace/commands/update-readme<br>
                                ./cogspace/commands/update-readme update<br>
                                ./cogspace/commands/update-readme status
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>What it updates:</strong>
                            <ul style="margin: 5px 0 0 20px;">
                                <li>COGSPACE version number</li>
                                <li>Code file count</li>
                                <li>Documentation file count</li>
                                <li>Test file count</li>
                                <li>Recent session achievements</li>
                            </ul>
                        </div>
                    </div>

                    <!-- new-project command -->
                    <div style="margin-bottom: 15px; border-left: 3px solid #aed581; padding-left: 15px;">
                        <div style="font-size: 1.1rem; font-weight: 600; color: #aed581; margin-bottom: 10px;">
                            🆕 new-project - Project Creation
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Purpose:</strong> Create new COGSPACE-enabled projects with full session management infrastructure.
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Syntax:</strong>
                            <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                                ./cogspace/commands/new-project<br>
                                ./cogspace/commands/new-project --name "my-project"<br>
                                ./cogspace/commands/new-project --help
                            </div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Modes:</strong>
                            <ul style="margin: 5px 0 0 20px;">
                                <li><strong>🏰 Crystal Palace:</strong> Projects created in /Volumes/FOUR-TB/root/</li>
                                <li><strong>📱 Portable:</strong> Projects created in ~/projects/</li>
                                <li><strong>⚠️ Standalone:</strong> Minimal project without DNA source</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Quick Reference Card -->
            <div class="story-section">
                <div class="story-title">⚡ Quick Reference</div>
                <div class="story-content">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
                        <div style="padding: 15px; background: #001d3d; border-radius: 8px;">
                            <div style="font-weight: 600; color: #64b5f6; margin-bottom: 10px;">Session Management</div>
                            <div style="font-family: monospace; font-size: 0.85rem; line-height: 1.8;">
                                <div>./hi → Start session</div>
                                <div>./save "msg" → Checkpoint</div>
                                <div>./bye "msg" → End session</div>
                            </div>
                        </div>
                        <div style="padding: 15px; background: #001d3d; border-radius: 8px;">
                            <div style="font-weight: 600; color: #81c784; margin-bottom: 10px;">Knowledge Commands</div>
                            <div style="font-family: monospace; font-size: 0.85rem; line-height: 1.8;">
                                <div>guidelines add/list/get</div>
                                <div>lessons add/list/get</div>
                                <div>note add/list</div>
                            </div>
                        </div>
                        <div style="padding: 15px; background: #001d3d; border-radius: 8px;">
                            <div style="font-weight: 600; color: #ef5350; margin-bottom: 10px;">Reporting Commands</div>
                            <div style="font-family: monospace; font-size: 0.85rem; line-height: 1.8;">
                                <div>trouble-report create/list</div>
                                <div>progress-report create/list</div>
                                <div>update-readme status/update</div>
                            </div>
                        </div>
                    </div>
                    <div style="margin-top: 15px; padding: 12px; background: #002855; border-radius: 6px; border-left: 3px solid #0466c8;">
                        <strong style="color: #64b5f6;">📍 Command Location:</strong>
                        <span style="font-family: monospace;">./cogspace/commands/&lt;command-name&gt;</span>
                    </div>
                </div>
            </div>

            <!-- v55.0.0: Database Architecture section -->
            <div class="story-section">
                <div class="story-title">🗄️ Database Architecture</div>
                <div class="story-content">
                    <div style="margin-bottom: 15px; padding: 15px; background: #002855; border-radius: 8px; border-left: 4px solid #ef5350;">
                        <strong style="color: #ef5350; font-size: 1.1rem;">⚠️ IMPORTANT: Two Database Locations</strong>
                        <p style="margin: 10px 0 0 0;">
                            COGSPACE has separate locations for database <em>utilities</em> vs. <em>data</em>. Don't confuse them!
                        </p>
                    </div>

                    <div style="margin: 20px 0;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem;">
                            <tr style="background: #001d3d;">
                                <th style="padding: 12px; text-align: left; border: 1px solid #0466c8;">Location</th>
                                <th style="padding: 12px; text-align: left; border: 1px solid #0466c8;">Purpose</th>
                                <th style="padding: 12px; text-align: left; border: 1px solid #0466c8;">Contents</th>
                            </tr>
                            <tr>
                                <td style="padding: 12px; border: 1px solid #0466c8; font-family: monospace; color: #64b5f6;">cogspace/db/</td>
                                <td style="padding: 12px; border: 1px solid #0466c8;"><strong>Utilities & Schema</strong></td>
                                <td style="padding: 12px; border: 1px solid #0466c8;">Python manager, schema.sql, helper code</td>
                            </tr>
                            <tr style="background: #001d3d;">
                                <td style="padding: 12px; border: 1px solid #0466c8; font-family: monospace; color: #81c784;">.cogspace/cogspace.db</td>
                                <td style="padding: 12px; border: 1px solid #0466c8;"><strong style="color: #81c784;">Runtime Session Data</strong></td>
                                <td style="padding: 12px; border: 1px solid #0466c8;">Actual sessions, memories, context (SQLite)</td>
                            </tr>
                        </table>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <strong>Project Structure:</strong>
                        <div style="margin: 10px 0; padding: 15px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.85rem; line-height: 1.6;">
                            my-project/<br>
                            ├── <span style="color: #81c784;">.cogspace/</span><br>
                            │   └── <span style="color: #81c784;">cogspace.db</span>    ← <span style="color: #81c784; font-weight: bold;">ACTUAL SESSION DATA</span><br>
                            ├── cogspace/<br>
                            │   └── db/<br>
                            │       ├── cogspace_db.py   ← Utilities<br>
                            │       └── schema.sql       ← Schema definitions<br>
                        </div>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <strong>Query Session Data:</strong>
                        <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.85rem;">
                            <div style="color: #888; margin-bottom: 5px;"># Find the database</div>
                            ls -la .cogspace/cogspace.db<br><br>
                            <div style="color: #888; margin-bottom: 5px;"># Query recent sessions</div>
                            sqlite3 .cogspace/cogspace.db "SELECT id, created_at, score FROM sessions ORDER BY created_at DESC LIMIT 5"
                        </div>
                    </div>

                    <div style="padding: 12px; background: #002855; border-radius: 6px; border-left: 3px solid #64b5f6;">
                        <strong style="color: #64b5f6;">💡 Why This Architecture?</strong>
                        <ul style="margin: 5px 0 0 20px; opacity: 0.9;">
                            <li><strong>Separation:</strong> Code (cogspace/db/) vs. Data (.cogspace/)</li>
                            <li><strong>Git-friendly:</strong> .cogspace/ is gitignored; session data stays local</li>
                            <li><strong>DNA-safe:</strong> Code syncs from DNA; runtime data is preserved</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Git Integration (moved to bottom v51.8.0) -->
            <div class="story-section">
                <div class="story-title">🔄 Git Auto-Sync</div>
                <div class="story-content">
                    <div style="margin-bottom: 15px;">
                        <strong>What is Git Auto-Sync?</strong>
                        <p style="margin: 10px 0;">
                            COGSPACE can automatically sync your code with GitHub on every wake and sleep cycle.
                            This ensures you never lose work and never work on stale code.
                        </p>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <strong>How it works:</strong>
                        <ul style="margin: 5px 0 0 20px;">
                            <li><strong>First time:</strong> COGSPACE detects GitHub remote and prompts you to enable auto-sync</li>
                            <li><strong>On wake (./hi):</strong> Auto-pulls latest changes from remote (prevents working on stale code)</li>
                            <li><strong>On sleep (./bye):</strong> Auto-commits and pushes all changes (ensures cloud backup)</li>
                        </ul>
                    </div>

                    <div style="margin-bottom: 15px; padding: 12px; background: #002855; border-radius: 6px; border-left: 3px solid #0466c8;">
                        <strong style="color: #64b5f6;">Default Behavior (Recommended):</strong>
                        <ul style="margin: 5px 0 0 20px;">
                            <li>Auto-sync is <strong>enabled by default</strong> (opt-out, not opt-in)</li>
                            <li>Aligns with COGSPACE 90%+ continuity promise</li>
                            <li>Protects against hardware failure and data loss</li>
                        </ul>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <strong>Disable auto-sync:</strong>
                        <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                            git config cogspace.autoSync.wake false<br>
                            git config cogspace.autoSync.sleep false
                        </div>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <strong>Enable auto-sync:</strong>
                        <div style="margin: 10px 0; padding: 10px; background: #001d3d; border-radius: 4px; font-family: monospace; font-size: 0.9rem;">
                            git config cogspace.autoSync.wake true<br>
                            git config cogspace.autoSync.sleep true
                        </div>
                    </div>
                </div>
            </div>

            <div class="story-section">
                <div class="story-title">📖 Git Basics</div>
                <div class="story-content">
                    <div style="margin-bottom: 15px;">
                        <strong>What is Git?</strong>
                        <p style="margin: 10px 0;">
                            Git is a version control system that tracks changes to your code over time.
                            It allows you to save snapshots of your work, collaborate with others, and recover from mistakes.
                        </p>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <strong>Core Git Concepts:</strong>
                        <ul style="margin: 5px 0 0 20px;">
                            <li><strong>Repository:</strong> The folder containing your code and its history</li>
                            <li><strong>Commit:</strong> A snapshot of your code at a specific point in time</li>
                            <li><strong>Remote:</strong> A copy of your repository hosted on GitHub (cloud backup)</li>
                            <li><strong>Branch:</strong> An independent line of development (main branch is default)</li>
                        </ul>
                    </div>

                    <div style="margin-bottom: 15px;">
                        <strong>Common Git Commands:</strong>
                        <div style="margin: 10px 0;">
                            <div style="margin-bottom: 10px; padding: 10px; background: #001d3d; border-radius: 4px;">
                                <div style="font-family: monospace; color: #64b5f6; margin-bottom: 5px;">git status</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">See which files have been modified</div>
                            </div>
                            <div style="margin-bottom: 10px; padding: 10px; background: #001d3d; border-radius: 4px;">
                                <div style="font-family: monospace; color: #64b5f6; margin-bottom: 5px;">git log</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">View commit history</div>
                            </div>
                            <div style="margin-bottom: 10px; padding: 10px; background: #001d3d; border-radius: 4px;">
                                <div style="font-family: monospace; color: #64b5f6; margin-bottom: 5px;">git pull</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">Download latest changes from remote</div>
                            </div>
                            <div style="margin-bottom: 10px; padding: 10px; background: #001d3d; border-radius: 4px;">
                                <div style="font-family: monospace; color: #64b5f6; margin-bottom: 5px;">git add .</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">Stage all changed files for commit</div>
                            </div>
                            <div style="margin-bottom: 10px; padding: 10px; background: #001d3d; border-radius: 4px;">
                                <div style="font-family: monospace; color: #64b5f6; margin-bottom: 5px;">git commit -m "message"</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">Create a snapshot with description</div>
                            </div>
                            <div style="margin-bottom: 10px; padding: 10px; background: #001d3d; border-radius: 4px;">
                                <div style="font-family: monospace; color: #64b5f6; margin-bottom: 5px;">git push</div>
                                <div style="font-size: 0.9rem; opacity: 0.8;">Upload commits to remote (cloud backup)</div>
                            </div>
                        </div>
                    </div>

                    <div style="padding: 12px; background: #002855; border-radius: 6px; border-left: 3px solid #0466c8;">
                        <strong style="color: #64b5f6;">💡 With COGSPACE Auto-Sync:</strong>
                        <p style="margin: 10px 0 0 0;">
                            You don't need to run these commands manually! COGSPACE handles git operations automatically
                            on wake and sleep cycles, ensuring your work is always backed up and synchronized.
                        </p>
                    </div>
                </div>
            </div>
        </div>
        </div>
    </div>

    <script>
        // All JavaScript inline - no external dependencies
        function switchTab(clickedTab, tabId) {
            // Remove 'active' class from all tabs
            const tabs = document.querySelectorAll('.tab-btn');
            tabs.forEach(tab => tab.classList.remove('active'));

            // Add 'active' class to the clicked tab
            clickedTab.classList.add('active');

            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            // Show selected tab content
            const targetContent = document.getElementById(tabId);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        }

        // Current filter state
        let currentRoleFilter = 'all';
        let currentSearchTerm = '';

        // Message filter function
        function filterMessages(role) {
            currentRoleFilter = role;

            // Update button states
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
                btn.style.background = btn.dataset.filter === 'all'
                    ? 'rgba(102, 126, 234, 0.1)'
                    : btn.dataset.filter === 'user'
                        ? 'rgba(74, 222, 128, 0.1)'
                        : 'rgba(245, 158, 11, 0.1)';
            });
            const activeBtn = document.querySelector('.filter-btn[data-filter="' + role + '"]');
            if (activeBtn) {
                activeBtn.classList.add('active');
                activeBtn.style.background = role === 'all'
                    ? 'rgba(102, 126, 234, 0.3)'
                    : role === 'user'
                        ? 'rgba(74, 222, 128, 0.3)'
                        : 'rgba(245, 158, 11, 0.3)';
            }

            // Apply combined filter
            applyFilters();
        }

        // Search messages function
        function searchMessages(term) {
            currentSearchTerm = term.toLowerCase().trim();
            const clearBtn = document.getElementById('clear-search-btn');
            const searchCount = document.getElementById('search-count');

            if (currentSearchTerm) {
                clearBtn.style.display = 'block';
            } else {
                clearBtn.style.display = 'none';
                searchCount.style.display = 'none';
            }

            applyFilters();
        }

        // Clear search function
        function clearSearch() {
            document.getElementById('message-search').value = '';
            currentSearchTerm = '';
            document.getElementById('clear-search-btn').style.display = 'none';
            document.getElementById('search-count').style.display = 'none';
            applyFilters();
        }

        // Apply both role filter and search filter
        function applyFilters() {
            let visibleCount = 0;
            let totalMatching = 0;

            document.querySelectorAll('#message-list .message').forEach(msg => {
                const matchesRole = currentRoleFilter === 'all' || msg.dataset.role === currentRoleFilter;
                const content = msg.querySelector('.message-content')?.textContent?.toLowerCase() || '';
                const matchesSearch = !currentSearchTerm || content.includes(currentSearchTerm);

                if (matchesRole && matchesSearch) {
                    msg.style.display = 'block';
                    visibleCount++;
                    // Highlight search term
                    if (currentSearchTerm) {
                        highlightText(msg.querySelector('.message-content'), currentSearchTerm);
                    } else {
                        removeHighlight(msg.querySelector('.message-content'));
                    }
                } else {
                    msg.style.display = 'none';
                }

                if (matchesRole) totalMatching++;
            });

            // Update search count
            const searchCount = document.getElementById('search-count');
            if (currentSearchTerm) {
                searchCount.textContent = visibleCount + ' found';
                searchCount.style.display = 'block';
                searchCount.style.color = visibleCount > 0 ? '#4ade80' : '#ef4444';
            }
        }

        // Highlight matching text
        function highlightText(element, term) {
            if (!element) return;
            removeHighlight(element);
            const html = element.innerHTML;
            // Escape regex special chars
            const escaped = term.replace(/[.*+?^$\{\}()|[\\]\\\\]/g, String.fromCharCode(92) + String.fromCharCode(36) + '&');
            const regex = new RegExp('(' + escaped + ')', 'gi');
            element.innerHTML = html.replace(regex, '<mark style="background: #f59e0b; color: #000; padding: 0 2px; border-radius: 2px;">' + String.fromCharCode(36) + '1</mark>');
        }

        // Remove highlight
        function removeHighlight(element) {
            if (!element) return;
            const markRegex = /<mark[^>]*>(.*?)<\\/mark>/gi;
            element.innerHTML = element.innerHTML.replace(markRegex, String.fromCharCode(36) + '1');
        }

        // Clock update functions
        function updateTimestamp() {
            const now = new Date();
            updateAnalogClock('pacific', 'America/Los_Angeles', now);
            updateAnalogClock('paraguay', 'America/Asuncion', now);
        }

        function updateAnalogClock(zone, timeZone, now) {
            const timeString = now.toLocaleTimeString('en-US', {
                timeZone: timeZone,
                hour: 'numeric',
                minute: 'numeric',
                hour12: true
            });

            const parts = timeString.match(/(\\d+):(\\d+)\\s*(AM|PM)/);
            if (!parts) return;

            let hours = parseInt(parts[1]);
            const minutes = parseInt(parts[2]);
            const ampm = parts[3];

            const hourAngle = (hours % 12) * 30 + minutes * 0.5;
            const minuteAngle = minutes * 6;

            const hourHand = document.getElementById(\`hour-hand-\${zone}\`);
            const minuteHand = document.getElementById(\`minute-hand-\${zone}\`);
            const ampmLabel = document.getElementById(\`ampm-\${zone}\`);

            if (hourHand) hourHand.style.transform = \`translateX(-50%) rotate(\${hourAngle}deg)\`;
            if (minuteHand) minuteHand.style.transform = \`translateX(-50%) rotate(\${minuteAngle}deg)\`;
            if (ampmLabel) ampmLabel.textContent = ampm;
        }

        // Initialize and update clocks
        updateTimestamp();
        setInterval(updateTimestamp, 1000);

        console.log('✅ COGSPACE Dashboard v33.0.0 loaded successfully');
        console.log('📊 Context data embedded and ready');
        console.log('🕐 Analog clocks initialized');
    </script>
</body>
</html>`;

  return html;
}

// Main execution
try {
  const context = getLatestContext();
  const semanticContext = getLatestSemanticContext(); // v40.2.0: Load semantic context
  const data = extractContextData(context);
  const html = generateHTML(context, semanticContext);

  // Ensure output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  // Write output file using sessionId from context
  const outputFile = path.join(OUTPUT_DIR, `dashboard-${data.sessionId}.html`);
  fs.writeFileSync(outputFile, html, 'utf8');

  console.log('');
  console.log(`✅ Dashboard generated successfully`);
  console.log(`📄 Output: ${outputFile}`);
  console.log(`📏 Size: ${(Buffer.byteLength(html) / 1024).toFixed(2)} KB`);
  if (semanticContext) {
    console.log(`🧠 Semantic context: ${semanticContext.sessionId}`);
  }
  console.log('');
  console.log(`🌐 Open in browser: file://${outputFile}`);
} catch (err) {
  console.error(`❌ Error: ${err.message}`);
  process.exit(1);
}


