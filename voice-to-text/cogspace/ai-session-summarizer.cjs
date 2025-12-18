#!/usr/bin/env node
// COGSPACE - see cogspace-version.json for version
// Generates rich, structured session artifacts using Claude-style compaction format
//
// This module creates meaningful session summaries for both human developers
// and successor AI instances resuming work.

const fs = require('fs');
const path = require('path');

// v53.0.0: Dynamic version display
const { getVersion } = require('./lib/version.cjs');

/**
 * ANTHROPIC COMPACTION FORMAT
 *
 * This schema mirrors the structure Claude uses when compacting context for
 * session continuation. It provides comprehensive coverage of:
 *
 * 1. Analysis - Chronological narrative of what happened
 * 2. Summary - Structured technical documentation
 *    - Primary Request/Intent
 *    - Key Technical Concepts
 *    - Files/Code Changes
 *    - Errors/Fixes
 *    - User Messages
 *    - Pending Tasks
 *    - Final System State
 */

const SEMANTIC_CONTEXT_SCHEMA = {
  version: "2.0.0",
  format: "anthropic-compaction",
  sections: [
    "chronologicalAnalysis",
    "primaryRequestIntent",
    "keyTechnicalConcepts",
    "filesAndChanges",
    "errorsAndFixes",
    "userMessages",
    "pendingTasks",
    "finalSystemState"
  ]
};

/**
 * Generate the AI summarization prompt template
 * This prompt instructs Claude (via API or manual analysis) to produce
 * structured session artifacts following Anthropic's compaction format.
 */
function generateSummarizationPrompt(sessionData) {
  const {
    sessionId,
    projectName,
    sleepMessage,
    rawMessages,
    toolUsage,
    filesModified,
    gitDiff,
    duration,
    timestamp,
    workNarrative,
    mentalModel,
    decisionContext
  } = sessionData;

  return `# COGSPACE Session Summarization Task

You are generating a session continuation artifact for COGSPACE v40.1.0.
This artifact will be used by both human developers and successor AI instances
to resume work effectively.

## Session Metadata
- **Session ID**: ${sessionId}
- **Project**: ${projectName}
- **Duration**: ${duration}
- **Timestamp**: ${timestamp}
- **Sleep Message**: ${sleepMessage}

## Input Context

### Raw Conversation Messages (${rawMessages?.length || 0} messages)
\`\`\`json
${JSON.stringify(rawMessages?.slice(-50) || [], null, 2)}
\`\`\`

### Tool Usage Summary
\`\`\`json
${JSON.stringify(toolUsage || {}, null, 2)}
\`\`\`

### Files Modified
\`\`\`
${filesModified?.join('\n') || 'No files modified'}
\`\`\`

### Git Diff Summary
\`\`\`
${gitDiff?.substring(0, 5000) || 'No git changes'}
\`\`\`

### Work Narrative (from COGSPACE)
\`\`\`json
${JSON.stringify(workNarrative || {}, null, 2)}
\`\`\`

### Mental Model (from COGSPACE)
\`\`\`json
${JSON.stringify(mentalModel || {}, null, 2)}
\`\`\`

### Decision Context (from COGSPACE)
\`\`\`json
${JSON.stringify(decisionContext || {}, null, 2)}
\`\`\`

---

## OUTPUT REQUIREMENTS

Generate a structured session artifact with these exact sections:

### 1. Chronological Analysis
Write a narrative analysis of the session in chronological order. Include:
- What work was requested initially
- Key decision points and pivots
- Problems encountered and how they were resolved
- Major accomplishments

### 2. Primary Request and Intent Summary
- **Primary Request**: What the user wanted (1-2 sentences)
- **Intent**: The underlying goal/purpose
- **Scope**: What was in-scope vs out-of-scope

### 3. Key Technical Concepts
List the main technical concepts, patterns, or frameworks involved.
Format: \`- **Concept Name**: Brief explanation\`

### 4. Files and Code Changes
For each significant file modified:
- **Path**: Full file path
- **Change Type**: Created | Modified | Deleted
- **Purpose**: Why this file was changed
- **Key Changes**: Important code modifications (with line references if available)

### 5. Errors and Fixes
Document any errors encountered:
- **Error**: What happened
- **Root Cause**: Why it happened
- **Fix Applied**: How it was resolved
- **Prevention**: How to avoid in future (if applicable)

### 6. User Messages Summary
Extract and categorize key user messages:
- **Instructions**: Direct requests from user
- **Feedback**: User's reactions and corrections
- **Decisions**: Choices user made when presented options

### 7. Pending Tasks
List any incomplete or follow-up tasks:
- **Task**: Description
- **Priority**: High | Medium | Low
- **Blockers**: Any known blockers

### 8. Final System State
- **Working State**: Is the system in a working state? What works/doesn't work?
- **Test Status**: Were tests run? Did they pass?
- **Deployment Status**: Any deployment-related information
- **Known Issues**: Remaining bugs or concerns

---

## FORMAT INSTRUCTIONS

- Use Markdown formatting
- Be specific and technical, not vague
- Include file paths, function names, line numbers when relevant
- Quote important user messages directly
- Prioritize information useful for resuming work
- Target length: 2000-4000 words for substantial sessions

Generate the artifact now:`;
}

/**
 * Extract raw data from COGSPACE cognitive context
 */
function extractSessionData(contextPath, projectRoot) {
  const data = {
    sessionId: null,
    projectName: path.basename(projectRoot),
    sleepMessage: process.argv[2] || 'Session completed',
    rawMessages: [],
    toolUsage: {},
    filesModified: [],
    gitDiff: null,
    duration: null,
    timestamp: new Date().toISOString(),
    workNarrative: null,
    mentalModel: null,
    decisionContext: null
  };

  // Read existing context file if available
  if (fs.existsSync(contextPath)) {
    try {
      const context = JSON.parse(fs.readFileSync(contextPath, 'utf8'));
      data.sessionId = context.sessionId;

      // Duration from mentalModel or serializedComponents
      data.duration = context.mentalModel?.progressMetrics?.sessionDuration ||
                      context.serializedComponents?.mentalModel?.progressMetrics?.sessionDuration;

      // Extract messages - check multiple locations
      // 1. Top-level messages array (current format)
      if (context.messages && Array.isArray(context.messages)) {
        data.rawMessages = context.messages;
      }
      // 2. serializedComponents.conversationAnalysis.userInteractions.messages
      else if (context.serializedComponents?.conversationAnalysis?.userInteractions?.messages) {
        data.rawMessages = context.serializedComponents.conversationAnalysis.userInteractions.messages;
      }
      // 3. Legacy contextStream format
      else if (context.serializedComponents?.contextStream?.messages) {
        data.rawMessages = context.serializedComponents.contextStream.messages;
      }

      // Extract tool usage from conversation analysis
      if (context.serializedComponents?.conversationAnalysis?.stats) {
        data.toolUsage = context.serializedComponents.conversationAnalysis.stats;
      }

      // Extract modified files from multiple locations
      if (context.mentalModel?.recentFiles) {
        data.filesModified = context.mentalModel.recentFiles;
      } else if (context.serializedComponents?.mentalModel?.recentFiles) {
        data.filesModified = context.serializedComponents.mentalModel.recentFiles;
      }

      // Extract rich context objects for AI analysis
      data.workNarrative = context.workNarrative || context.serializedComponents?.workNarrative;
      data.mentalModel = context.mentalModel || context.serializedComponents?.mentalModel;
      data.decisionContext = context.serializedComponents?.decisionContext;

    } catch (err) {
      console.error('Error reading context file:', err.message);
    }
  }

  // Get git diff
  try {
    const { execSync } = require('child_process');
    data.gitDiff = execSync('git diff HEAD~1 --stat', {
      cwd: projectRoot,
      encoding: 'utf8',
      maxBuffer: 10 * 1024 * 1024
    }).substring(0, 10000);
  } catch (err) {
    data.gitDiff = null;
  }

  return data;
}

/**
 * Generate semantic context structure ready for Claude analysis
 * @param {Object} sessionData - Extracted session data
 * @param {Object|null} analysisResult - AI-generated analysis (if available)
 * @param {string} userReflections - User's reflections about the session (v40.2.0)
 */
function generateSemanticContextStructure(sessionData, analysisResult = null, userReflections = '') {
  const now = new Date();

  return {
    version: SEMANTIC_CONTEXT_SCHEMA.version,
    format: SEMANTIC_CONTEXT_SCHEMA.format,
    generatedAt: now.toISOString(),
    sessionId: sessionData.sessionId,
    projectName: sessionData.projectName,

    // If we have AI-generated analysis, use it
    // Otherwise, provide the prompt for manual generation
    analysis: analysisResult ? {
      status: "generated",
      content: analysisResult
    } : {
      status: "pending",
      prompt: generateSummarizationPrompt(sessionData),
      instructions: "Run this prompt through Claude to generate the full analysis"
    },

    // Structured sections (populated by AI or partially extracted)
    sections: {
      chronologicalAnalysis: analysisResult?.chronologicalAnalysis || null,
      primaryRequestIntent: analysisResult?.primaryRequestIntent || {
        request: sessionData.sleepMessage,
        intent: "Session work completion",
        scope: "See conversation history for details"
      },
      keyTechnicalConcepts: analysisResult?.keyTechnicalConcepts || [],
      filesAndChanges: sessionData.filesModified.map(f => ({
        path: f,
        changeType: "modified",
        purpose: "See git history for details"
      })),
      errorsAndFixes: analysisResult?.errorsAndFixes || [],
      userMessages: extractUserMessages(sessionData.rawMessages),
      pendingTasks: analysisResult?.pendingTasks || [],
      finalSystemState: analysisResult?.finalSystemState || {
        workingState: "See session completion status",
        testStatus: "Not automatically verified",
        deploymentStatus: "N/A",
        knownIssues: []
      },
      // v40.2.0: User reflections for "What's Next?" tab
      userReflections: userReflections || sessionData.userReflections || null
    },

    // Raw data for context
    rawData: {
      messageCount: sessionData.rawMessages.length,
      toolUsage: sessionData.toolUsage,
      duration: sessionData.duration,
      timestamp: sessionData.timestamp
    }
  };
}

/**
 * Extract and categorize user messages from conversation
 */
function extractUserMessages(messages) {
  const userMessages = {
    instructions: [],
    feedback: [],
    decisions: []
  };

  if (!Array.isArray(messages)) return userMessages;

  for (const msg of messages) {
    if (msg.role !== 'user' || !msg.content) continue;

    const content = typeof msg.content === 'string' ? msg.content :
                    (msg.content[0]?.text || JSON.stringify(msg.content));
    const timestamp = msg.timestamp || null;

    // Categorize based on content patterns
    if (content.match(/^(yes|no|[12345]|option|let'?s? (go|do)|confirm|proceed)/i)) {
      userMessages.decisions.push({ content: content.substring(0, 500), timestamp });
    } else if (content.match(/^(good|great|perfect|wrong|no,|actually|wait|hmm|i see)/i)) {
      userMessages.feedback.push({ content: content.substring(0, 500), timestamp });
    } else {
      userMessages.instructions.push({ content: content.substring(0, 500), timestamp });
    }
  }

  return userMessages;
}

/**
 * Main execution
 */
async function main() {
  const projectRoot = process.cwd();
  const sessionId = process.argv[2] || `${Date.now()}-manual`;
  const sleepMessage = process.argv[3] || 'Session completed';
  const userReflections = process.argv[4] || ''; // v40.2.0: User reflections for What's Next tab

  console.log(`🧠 COGSPACE AI Session Summarizer ${getVersion().display}`);
  console.log('=========================================');
  console.log(`Project: ${path.basename(projectRoot)}`);
  console.log(`Session: ${sessionId}`);
  console.log(`Message: ${sleepMessage}`);
  if (userReflections) {
    console.log(`Reflections: ${userReflections.substring(0, 50)}${userReflections.length > 50 ? '...' : ''}`);
  }
  console.log('');

  // Find most recent context file
  const contextDir = path.join(projectRoot, 'session-management', 'cognitive-context');
  let contextPath = null;

  if (fs.existsSync(contextDir)) {
    // v53.0.0: Fix file selection - use mtime (modification time) instead of alphabetic sort
    // This fixes the bug where 'complete-context-welcome-*' sorted after numeric session IDs
    const files = fs.readdirSync(contextDir)
      .filter(f => f.startsWith('complete-context-') && f.endsWith('.json'))
      .map(f => {
        try {
          return {
            name: f,
            mtime: fs.statSync(path.join(contextDir, f)).mtimeMs
          };
        } catch (e) {
          return { name: f, mtime: 0 };
        }
      })
      .sort((a, b) => b.mtime - a.mtime)  // Most recent first by modification time
      .map(f => f.name);

    if (files.length > 0) {
      contextPath = path.join(contextDir, files[0]);
      console.log(`📂 Found context: ${files[0]} (most recent by mtime)`);
    }
  }

  // Extract session data
  const sessionData = extractSessionData(contextPath, projectRoot);
  sessionData.sleepMessage = sleepMessage;
  sessionData.userReflections = userReflections; // v40.2.0: Add user reflections
  if (!sessionData.sessionId) sessionData.sessionId = sessionId;

  // Generate semantic context structure (pass userReflections)
  const semanticContext = generateSemanticContextStructure(sessionData, null, userReflections);

  // Write semantic context
  const outputPath = path.join(contextDir, `semantic-context-${sessionId}.json`);
  fs.writeFileSync(outputPath, JSON.stringify(semanticContext, null, 2));
  console.log(`\n✅ Semantic context structure written to:`);
  console.log(`   ${outputPath}`);

  // Also write the prompt for manual Claude analysis
  const promptPath = path.join(contextDir, `summarization-prompt-${sessionId}.md`);
  fs.writeFileSync(promptPath, generateSummarizationPrompt(sessionData));
  console.log(`\n📝 Summarization prompt written to:`);
  console.log(`   ${promptPath}`);

  // Output summary for session-sleep.sh to capture
  console.log('\n--- SEMANTIC CONTEXT GENERATED ---');
  console.log(`SEMANTIC_PATH=${outputPath}`);
  console.log(`PROMPT_PATH=${promptPath}`);
  console.log(`MESSAGE_COUNT=${sessionData.rawMessages.length}`);
  console.log(`FILES_MODIFIED=${sessionData.filesModified.length}`);

  return { semanticContext, outputPath, promptPath };
}

// Export for use as module
module.exports = {
  generateSummarizationPrompt,
  extractSessionData,
  generateSemanticContextStructure,
  extractUserMessages,
  SEMANTIC_CONTEXT_SCHEMA
};

// Run if called directly
if (require.main === module) {
  main().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
  });
}
