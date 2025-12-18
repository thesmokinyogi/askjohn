#!/usr/bin/env node
// COGSPACE - see cogspace-version.json for version
/**
 * SESSION SUMMARY GENERATOR
 * Generates human-readable session-summary.json from complete-context-*.json
 * v21.3.1 "Ideaplace - Full Context"
 */

const fs = require('fs');
const path = require('path');

class SessionSummaryGenerator {
    constructor(projectPath = process.cwd()) {
        this.projectPath = projectPath;
        this.contextDir = path.join(projectPath, 'session-management', 'cognitive-context');
        this.summariesDir = path.join(this.contextDir, 'summaries');
        this.ensureDirectories();
    }

    ensureDirectories() {
        if (!fs.existsSync(this.summariesDir)) {
            fs.mkdirSync(this.summariesDir, { recursive: true });
        }
    }

    getLatestCompleteContext() {
        try {
            const files = fs.readdirSync(this.contextDir);
            const contextFiles = files.filter(f => f.startsWith('complete-context-')).sort().reverse();
            if (contextFiles.length > 0) {
                const latestFile = path.join(this.contextDir, contextFiles[0]);
                return JSON.parse(fs.readFileSync(latestFile, 'utf8'));
            }
        } catch (err) {
            console.error('❌ Error reading complete-context:', err.message);
            return null;
        }
        return null;
    }

    getRecentNotes() {
        const notesDir = path.join(this.contextDir, 'notes');
        try {
            if (!fs.existsSync(notesDir)) {
                return [];
            }
            const noteFiles = fs.readdirSync(notesDir)
                .filter(f => f.endsWith('.json'))
                .sort()
                .reverse()
                .slice(0, 5); // Get 5 most recent

            return noteFiles.map(file => {
                try {
                    const noteData = JSON.parse(fs.readFileSync(path.join(notesDir, file), 'utf8'));
                    return {
                        timestamp: noteData.timestamp,
                        developer: noteData.developer,
                        content: noteData.content
                    };
                } catch (err) {
                    return null;
                }
            }).filter(note => note !== null);
        } catch (err) {
            return [];
        }
    }

    generateSummary(completeContext) {
        if (!completeContext) {
            return null;
        }

        const mental = completeContext.mentalModel || {};
        const narrative = completeContext.workNarrative || {};
        const decisions = completeContext.decisionContext || {};
        const performance = completeContext.performanceDeltas || {};
        const cognitive = mental.cognitiveState || {};
        const notes = this.getRecentNotes();

        // Get values with fallbacks
        const workDescription = mental.workDescription || narrative.sessionStory || "Work session in progress";
        const currentFocus = mental.currentFocus || narrative.currentChapter || "";
        const sessionStory = narrative.sessionStory || workDescription;
        const currentChapter = narrative.currentChapter || currentFocus;
        const nextChapter = narrative.nextChapter || "";
        const nextActions = Array.isArray(mental.nextActions) ? mental.nextActions : [];
        const blockingIssues = Array.isArray(mental.blockingIssues) ? mental.blockingIssues.filter(i => i && i !== 'None') : [];
        const achievements = Array.isArray(narrative.achievements) ? narrative.achievements : [];
        const challenges = Array.isArray(narrative.challenges) ?
            narrative.challenges.map(c => typeof c === 'string' ? c : (c.challenge || '')).filter(c => c && c !== 'None') : [];

        // Process decisions
        const recentDecisions = Array.isArray(decisions.chosenPaths) ? decisions.chosenPaths.map(path => ({
            approach: path.approach || '',
            rationale: path.rationale || '',
            confidence: Math.round((path.confidenceInChoice || path.confidence || 0) * 100)
        })) : [];

        // Process improvements
        const improvements = Array.isArray(performance.improvements) ? performance.improvements.map(imp => {
            const metric = imp.metric || '';
            const before = performance.baseline ? (performance.baseline[metric.toLowerCase()] || 0) : 0;
            const after = performance.currentMetrics ? (performance.currentMetrics[metric.toLowerCase()] || 0) : 0;
            const delta = after - before;
            return {
                metric,
                before,
                after,
                delta
            };
        }) : [];

        // Build summary
        const summary = {
            meta: {
                sessionId: completeContext.sessionId || '',
                projectName: completeContext.projectName || '',
                timestamp: completeContext.timestamp || new Date().toISOString(),
                continuityScore: completeContext.continuityScore || 0,
                sessionDuration: mental.progressMetrics?.sessionDuration || "00:00",
                saveCount: mental.progressMetrics?.saveCount || 0
            },
            workState: {
                description: workDescription,
                currentFocus: currentFocus,
                currentChapter: currentChapter,
                nextChapter: nextChapter,
                sessionStory: sessionStory
            },
            planned: {
                nextActions: nextActions,
                blockingIssues: blockingIssues
            },
            progress: {
                achievements: achievements,
                challenges: challenges
            },
            notes: {
                recentNotes: notes,
                totalNoteCount: notes.length,
                lastNoteTimestamp: notes.length > 0 ? notes[0].timestamp : null
            },
            cognitiveState: {
                understanding: Math.round((cognitive.understandingLevel || 0) * 100),
                complexity: Math.round((cognitive.problemComplexity || 0) * 100),
                velocity: Math.round((cognitive.progressVelocity || 0) * 100),
                confidence: Math.round((cognitive.confidenceLevel || 0) * 100)
            },
            decisions: {
                recent: recentDecisions
            },
            metrics: {
                improvements: improvements
            }
        };

        return summary;
    }

    async saveSummary(summary) {
        if (!summary) {
            return false;
        }

        // Save primary session-summary.json
        const summaryPath = path.join(this.contextDir, 'session-summary.json');
        fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));

        // Save historical snapshot
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const snapshotPath = path.join(this.summariesDir, `session-summary-${timestamp}.json`);
        fs.writeFileSync(snapshotPath, JSON.stringify(summary, null, 2));

        return true;
    }

    async run() {
        console.log('📊 Generating session summary...');

        const completeContext = this.getLatestCompleteContext();
        if (!completeContext) {
            console.error('❌ No complete-context file found');
            return false;
        }

        const summary = this.generateSummary(completeContext);
        if (!summary) {
            console.error('❌ Failed to generate summary');
            return false;
        }

        const saved = await this.saveSummary(summary);
        if (saved) {
            console.log('✅ Session summary generated successfully');
            console.log(`📄 File: session-management/cognitive-context/session-summary.json`);
            return true;
        }

        return false;
    }
}

module.exports = SessionSummaryGenerator;

// CLI Usage
if (require.main === module) {
    const generator = new SessionSummaryGenerator();
    generator.run().then(success => {
        process.exit(success ? 0 : 1);
    });
}


