#!/usr/bin/env node
// COGSPACE - see cogspace-version.json for version

const fs = require('fs');
const path = require('path');

// v53.0.0: Dynamic version display
const { getVersion } = require('./lib/version.cjs');

async function generateCompleteContext(sessionId, timestamp, sleepMessage, workSummary, achievements, challenges, nextPriority, performance, sessionDuration) {
    try {
        // Load required modules
        const CognitiveWorkspaceSerializer = require('./analyzers/serializer.cjs');
        const ContextAnalyzer = require('./analyzers/context-analyzer.cjs');

        const serializer = new CognitiveWorkspaceSerializer();
        const analyzer = new ContextAnalyzer();

        // 🆕 v32.0.0: Load v32 enhancement modules
        let semanticContext, gitChanges, userContext;
        let SemanticAnalyzer, analyzeGitChanges, UserContextAnalyzer;
        let v32Available = false;

        try {
            const semanticAnalyzerModule = require('./analyzers/semantic-analyzer.cjs');
            SemanticAnalyzer = semanticAnalyzerModule.analyzeSemanticContext; // It's a function, not a class
            const gitAnalyzer = require('./analyzers/git-diff-analyzer.cjs');
            analyzeGitChanges = gitAnalyzer.analyzeGitChanges;
            UserContextAnalyzer = require('./analyzers/user-context-analyzer.cjs');

            v32Available = true;
            console.log(`🧠 ${getVersion().display}: Enhanced analyzers loaded`);
        } catch (v32LoadError) {
            console.log('⚠️  v32 analyzers not available, using v30/v31 context generation');
        }

        let canvasContext;

        try {
            // 🎯 CANVAS-CATCHER INTEGRATION (restored 2025-11-12)
            // Three-tier fallback: Claude Code JSONL (85%) → Git Diff (40%) → Basic (20%)

            // TIER 1: Try Claude Code JSONL extraction (HIGH FIDELITY)
            const ClaudeCodeContextExtractor = require('./claude-code-context-extractor.cjs');
            const claudeCodeExtractor = new ClaudeCodeContextExtractor(process.cwd());
            const claudeCodeContext = await claudeCodeExtractor.extractSessionContext(120);

            if (claudeCodeContext) {
                console.log('✅ Using Claude Code JSONL context (85-90% conversation fidelity)');
                canvasContext = claudeCodeContext;
            } else {
                // TIER 2: Fallback to git diff analysis (MEDIUM FIDELITY)
                console.log('⚠️  No Claude Code session found, using git diff analysis (40% fidelity)');
                canvasContext = await analyzer.captureCanvasContext(sessionId, sleepMessage, workSummary);
            }
        } catch (analyzerError) {
            // TIER 3: Emergency fallback to basic context (LOW FIDELITY)
            console.log('⚠️ Both extractors failed, using basic context generation (20% fidelity)');
            canvasContext = {
                workDescription: workSummary || 'Session completed',
                currentFocus: 'Session termination',
                progressArc: 'Session completion',
                currentChapter: 'Final session tasks',
                nextChapter: 'Next session preparation',
                achievements: achievements ? achievements.split(',').map(a => ({ achievement: a.trim(), timestamp })) : [],
                challenges: challenges ? challenges.split(',').map(c => ({ challenge: c.trim(), status: 'pending' })) : [],
                nextActions: nextPriority ? [nextPriority] : ['Continue work'],
                immediateActions: [],
                extractionMetadata: {
                    source: 'basic-fallback',
                    extractionQuality: 'low-fidelity',
                    error: analyzerError.message
                }
            };
        }

        // 🆕 v32.0.0: Run enhanced analyzers if available
        if (v32Available) {
            try {
                const userContextAnalyzer = new UserContextAnalyzer();

                // Prepare session data for analyzers
                const sessionData = {
                    sessionId,
                    timestamp,
                    projectName: path.basename(process.cwd()),
                    workDescription: canvasContext.workDescription,
                    currentFocus: canvasContext.currentFocus,
                    achievements: canvasContext.achievements,
                    challenges: canvasContext.challenges,
                    nextActions: canvasContext.nextActions,
                    toolUsage: canvasContext.toolUsage || [],
                    userMessages: canvasContext.userMessages || []
                };

                // Run semantic analysis (it's a function, not a class method)
                semanticContext = SemanticAnalyzer(sessionData);
                console.log('  ✅ Semantic analysis complete (what/why/how)');

                // Run git diff analysis
                gitChanges = analyzeGitChanges(process.cwd());
                console.log(`  ✅ Git changes analyzed: ${gitChanges.summary}`);

                // Run user context analysis
                userContext = userContextAnalyzer.analyzeUserContext(sessionData);
                console.log('  ✅ User context tracking complete');

            } catch (v32AnalyzerError) {
                console.log('⚠️  v32 analyzer execution failed:', v32AnalyzerError.message);
                // Continue with v30/v31 context generation
            }
        }
        
        // Use canvas context achievements and challenges instead of generic ones
        // FIX 2025-10-29: Filter empty strings per Howard's directive
        const achievementsArray = canvasContext.achievements.length > 0 ?
            canvasContext.achievements :
            (achievements ? achievements.split(',').filter(a => a.trim()).map(a => ({
                achievement: a.trim(),
                timestamp: timestamp
            })) : []);

        const challengesArray = canvasContext.challenges.length > 0 ?
            canvasContext.challenges :
            (challenges ? challenges.split(',').filter(c => c.trim()).map(c => ({
                challenge: c.trim(),
                status: "pending"
            })) : []);
        
        // Generate all cognitive components with enhanced context
        const mentalModel = await serializer.captureActiveContext(
            canvasContext.workDescription,
            canvasContext.currentFocus,
            {
                achievementsCount: achievementsArray.length,
                challengesCount: challengesArray.length,
                sessionDuration: sessionDuration || "00:00:00", // FIX 2025-10-29: Use actual session duration
                completionStatus: "Session terminated with preserved context",
                sleepMessage: canvasContext.sleepMessage || sleepMessage  // 🔧 FIX 2025-11-12: Preserve user's bye message
            },
            challengesArray.map(c => typeof c === 'string' ? c : c.challenge),
            canvasContext.nextActions
        );
        
        const workNarrative = await serializer.buildWorkNarrative(
            canvasContext.workDescription,
            canvasContext.progressArc,
            canvasContext.currentChapter,
            canvasContext.nextChapter,
            achievementsArray,
            challengesArray
        );
        
        // 🔧 FIX 2025-11-12: Use Canvas-Catcher decision extraction
        // If Canvas-Catcher provided decisions, use them; otherwise use empty arrays
        const decisions = canvasContext.decisions || { rejectedPaths: [], chosenPaths: [], tradeOffs: [] };
        const decisionContext = await serializer.archiveDecisionContext(
            decisions.rejectedPaths || [],
            decisions.chosenPaths || [],
            decisions.tradeOffs || [],
            []   // evidence - to be enhanced in future version
        );
        
        // FIX 2025-10-29: Remove hardcoded performance metrics per Howard's directive
        // Metrics will be properly defined and measured in future version
        const performanceDeltas = {
            timestamp: new Date().toISOString(),
            sessionId: sessionId,
            note: "Performance metrics collection to be implemented - placeholder only"
        };
        
        const executableContinuity = await serializer.generateExecutableContinuity(
            canvasContext.immediateActions || [{
                description: "Continue current work session objectives",
                command: null,
                priority: "normal",
                context: "Generated from canvas analysis"
            }],
            [{
                step: "Verify complete context preservation",
                command: "jq . session-management/cognitive-context/complete-context-*.json | tail -1"
            }],
            [{
                step: "Restore from cognitive backups",
                command: "cp session-management/cognitive-context/backups/* session-management/cognitive-context/"
            }]
        );
        
        const portableContext = await serializer.createPortableContext();

        // 🆕 v32.0.0: Build enhanced context with v32 components
        const contextComponents = {
            mentalModel,
            workNarrative,
            decisionContext,
            performanceDeltas,
            executableContinuity,
            portableContext
        };

        // Add v32 enhancements if available
        if (semanticContext) {
            contextComponents.semanticContext = semanticContext;
        }
        if (gitChanges) {
            contextComponents.gitChanges = gitChanges;
        }
        if (userContext) {
            contextComponents.userContext = userContext;
        }

        // 🆕 v32.1.0: Add full message transcript from Canvas-Catcher
        if (canvasContext.messages && canvasContext.messages.length > 0) {
            contextComponents.messages = canvasContext.messages;
        }

        // 🆕 v56.0.0: Add distributed consciousness manifest
        if (canvasContext.sessionManifest) {
            contextComponents.sessionManifest = canvasContext.sessionManifest;
        }
        if (canvasContext.distributedNodes && canvasContext.distributedNodes.length > 0) {
            contextComponents.distributedNodes = canvasContext.distributedNodes;
        }

        // Generate complete context
        const completeContext = await serializer.serializeCompleteWorkspace(contextComponents);
        
        console.log(`✅ Complete cognitive context generated: session-management/cognitive-context/complete-context-${sessionId}.json`);
        return true;
        
    } catch (error) {
        console.error('❌ Error generating complete context:', error.message);
        return false;
    }
}

// CLI Usage
if (require.main === module) {
    const [sessionId, timestamp, sleepMessage, workSummary, achievements, challenges, nextPriority, performance, sessionDuration] = process.argv.slice(2);

    if (!sessionId || !timestamp) {
        console.error("❌ ERROR: Missing required parameters");
        console.error("Usage: node generate-complete-context.js <sessionId> <timestamp> <sleepMessage> <workSummary> <achievements> <challenges> <nextPriority> <performance> [sessionDuration]");
        process.exit(1);
    }

    // FIX 2025-10-29: Proper async/await handling per Howard's directive
    generateCompleteContext(sessionId, timestamp, sleepMessage, workSummary, achievements, challenges, nextPriority, performance, sessionDuration)
        .then(() => {
            process.exit(0);
        })
        .catch(err => {
            console.error('❌ Fatal error:', err.message);
            process.exit(1);
        });
}

module.exports = { generateCompleteContext };


