#!/usr/bin/env node
// COGSPACE v40.0.0
/**
 * WELCOME CONTEXT GENERATOR
 * Creates properly formatted welcome context using CognitiveWorkspaceSerializer
 * Replaces static template to ensure serializer validation passes
 */

const path = require('path');
const fs = require('fs');

// Import the serializer
const CognitiveWorkspaceSerializer = require('./analyzers/serializer.cjs');

async function createWelcomeContext(projectPath = process.cwd()) {
    const projectName = path.basename(projectPath);
    const serializer = new CognitiveWorkspaceSerializer(projectPath);

    console.log(`\x1b[36m🎉 Creating welcome context for ${projectName}...\x1b[0m`);

    // Welcome context data
    const welcomeData = {
        mentalModel: {
            workDescription: `Welcome to COGSPACE! This is your cognitive workspace where memories are stored and work context is preserved across sessions.`,
            currentFocus: `Getting started with ${projectName}`,
            progressMetrics: {
                sessionCount: 1,
                contextVersion: "23.1.3",
                welcomeGenerated: new Date().toISOString()
            },
            blockingIssues: [],
            nextActions: [
                "Start working on your project",
                "Your work will be automatically saved with 'bye'",
                "Resume anytime with 'hi' command"
            ]
        },
        workNarrative: {
            sessionStory: "This is your first COGSPACE session! As you work together with Claude Code, we'll build a shared understanding of your project.",
            progressArc: "Beginning → Active Development → Continuous Improvement",
            currentChapter: "Welcome & Initialization",
            nextChapter: "Active Development",
            achievements: [
                "COGSPACE initialized successfully",
                "Cognitive context system ready",
                "Session management active"
            ],
            challenges: []
        },
        decisionContext: {
            rejectedPaths: [],
            chosenPaths: [
                {
                    decision: "Initialize COGSPACE v23.1.3",
                    reasoning: "Modern cognitive workspace with session persistence",
                    timestamp: new Date().toISOString()
                }
            ],
            tradeOffs: [],
            evidence: [
                "First-time project initialization",
                "No previous context found",
                "Welcome context generated"
            ]
        },
        performanceDeltas: {
            before: {},
            after: {
                cogspaceVersion: "23.1.3",
                sessionManagement: "active",
                contextPersistence: "enabled"
            },
            improvements: [
                "COGSPACE cognitive workspace initialized",
                "Session persistence enabled",
                "Dashboard generation ready"
            ],
            regressions: []
        },
        continuityData: {
            dependencies: {
                cogspaceVersion: "23.1.3",
                nodeVersion: process.version,
                platform: process.platform
            },
            recommendations: [
                "Use 'hi' to start sessions",
                "Use 'bye <message>' to save context",
                "Use 'save <message>' for mid-session saves",
                "View your dashboard at http://localhost:8765"
            ],
            nextActions: [
                {
                    action: "Start working on your project",
                    priority: "high",
                    context: "Ready for development"
                }
            ]
        }
    };

    // Serialize complete workspace with welcome data
    const completeContext = await serializer.serializeCompleteWorkspace(welcomeData);

    // Save to both locations for compatibility
    const contextDir = path.join(projectPath, 'session-management', 'cognitive-context');
    const memoriesDir = path.join(projectPath, 'memories');

    // Ensure directories exist
    if (!fs.existsSync(memoriesDir)) {
        fs.mkdirSync(memoriesDir, { recursive: true });
    }

    const sessionId = serializer.sessionId;
    const contextFile = `complete-context-welcome-${sessionId}.json`;

    // Save to session-management/cognitive-context/
    const contextPath = path.join(contextDir, contextFile);
    await fs.promises.writeFile(
        contextPath,
        JSON.stringify(completeContext, null, 2)
    );

    // Also save to memories/ for compatibility
    const memoriesPath = path.join(memoriesDir, contextFile);
    await fs.promises.writeFile(
        memoriesPath,
        JSON.stringify(completeContext, null, 2)
    );

    console.log(`\x1b[32m✅ Welcome context created: ${contextFile}\x1b[0m`);
    console.log(`\x1b[36m📝 Location: session-management/cognitive-context/ and memories/\x1b[0m`);
    console.log(`\x1b[36m🎯 Session ID: welcome-${sessionId}\x1b[0m`);

    // Return session ID for shell script to use
    console.log(`SESSION_ID=welcome-${sessionId}`);

    return sessionId;
}

// Run if called directly
if (require.main === module) {
    const projectPath = process.argv[2] || process.cwd();
    createWelcomeContext(projectPath).catch(err => {
        console.error('\x1b[31m❌ Failed to create welcome context:\x1b[0m', err.message);
        process.exit(1);
    });
}

module.exports = createWelcomeContext;


