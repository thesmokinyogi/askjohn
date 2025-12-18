#!/usr/bin/env node
// COGSPACE - see cogspace-version.json for version
/**
 * Claude Code Context Extractor
 * Parses Claude Code JSONL files to feed cognitive-serializer
 * Integrated with Canvas-Catcher parsing logic
 *
 * Version History:
 * - 1.0.0: Initial implementation
 * - 1.1.0: Fixed agent JSONL exclusion bug
 * - 2.0.0: v52.0.0 Distributed Consciousness Preservation
 *          - Multi-file session capture (main + all agents)
 *          - Session manifest generation
 *          - Wake/sleep timestamp-based timeframe
 *          - Original artifact preservation
 * - 2.1.0: v53.0.0 Dynamic version display
 * - 2.2.0: Agent ID Preservation
 *          - Preserve agentId in message output for db-session-save.py
 *          - Preserve sessionType ('primary' or 'agent')
 *          - Enables multi-consciousness attribution in database
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// v53.0.0: Dynamic version display
const { getVersion } = require('./lib/version.cjs');

class ClaudeCodeContextExtractor {
    constructor(projectPath) {
        this.projectPath = projectPath;
        this.claudeDir = path.join(os.homedir(), '.claude', 'projects');
    }

    /**
     * v52.0.0: Main entry point - now uses distributed consciousness capture
     * @param {Object} options - Extraction options
     * @param {number} options.sessionDurationMinutes - Fallback duration (default 120)
     * @param {string} options.wakeTimestamp - ISO timestamp of session wake (optional)
     * @param {string} options.sleepTimestamp - ISO timestamp of session sleep (optional)
     * @returns {Object} Extracted and merged context
     */
    async extractSessionContext(options = {}) {
        // Support legacy call signature: extractSessionContext(120)
        if (typeof options === 'number') {
            options = { sessionDurationMinutes: options };
        }

        const {
            sessionDurationMinutes = 120,
            wakeTimestamp = null,
            sleepTimestamp = null
        } = options;

        try {
            const projectName = this.normalizeProjectPath(this.projectPath);
            const projectDir = path.join(this.claudeDir, projectName);

            if (!fs.existsSync(projectDir)) {
                console.log('⚠️  No Claude Code session found for this project');
                return null;
            }

            console.log(`🧠 ${getVersion().full}: Distributed consciousness capture active`);

            // v52.0.0: Calculate timeframe from wake/sleep timestamps
            let startTime, endTime;
            if (wakeTimestamp && sleepTimestamp) {
                // Use wake/sleep with 1-minute padding on each side
                startTime = new Date(wakeTimestamp).getTime() - (60 * 1000);
                endTime = new Date(sleepTimestamp).getTime() + (60 * 1000);
                console.log(`📅 Session timeframe: ${wakeTimestamp} → ${sleepTimestamp} (+/- 1 min padding)`);
            } else {
                // Fallback to duration-based
                endTime = Date.now();
                startTime = endTime - (sessionDurationMinutes * 60 * 1000);
                console.log(`📅 Using duration-based timeframe: last ${sessionDurationMinutes} minutes`);
            }

            // v52.0.0: Find ALL session files from timeframe
            const allFiles = this.findAllSessionFiles(projectDir, startTime, endTime);

            if (allFiles.length === 0) {
                console.log('⚠️  No session files found in timeframe');
                return null;
            }

            // Categorize and create manifest
            const { primary, agents, manifest } = this.categorizeSessionFiles(allFiles);

            console.log(`✅ Found ${allFiles.length} session files:`);
            console.log(`   📍 Main sessions: ${manifest.mainSessionCount}`);
            console.log(`   🤖 Agent sessions: ${manifest.agentSessionCount}`);

            // v52.0.0: Parse and merge all files
            const sessionData = await this.extractDistributedContext(allFiles, startTime, endTime);

            if (!sessionData || sessionData.messages.length === 0) {
                console.log('⚠️  No messages found in session files');
                return null;
            }

            console.log(`✅ Merged ${sessionData.messages.length} messages, ${sessionData.toolCalls.length} tool calls`);
            console.log(`🧩 Distributed nodes captured: ${sessionData.distributedNodes.length}`);

            // Transform for serializer (includes manifest)
            return this.transformForSerializer(sessionData, manifest);

        } catch (error) {
            console.error('🚨 Claude Code extraction error:', error.message);
            return null;
        }
    }

    normalizeProjectPath(projectPath) {
        // Convert /Volumes/FOUR-TB/root/clarity-operations
        // to -Volumes-FOUR-TB-root-clarity-operations
        // NOTE: Leading dash IS required, don't strip it
        return projectPath.replace(/\//g, '-');
    }

    /**
     * v52.0.0: Find ALL session files modified within timeframe
     */
    findAllSessionFiles(projectDir, startTime, endTime) {
        try {
            const allFiles = fs.readdirSync(projectDir)
                .filter(f => f.endsWith('.jsonl'))
                .map(f => {
                    const filePath = path.join(projectDir, f);
                    const stats = fs.statSync(filePath);
                    return {
                        path: filePath,
                        filename: f,
                        mtime: stats.mtimeMs,
                        size: stats.size,
                        isAgent: f.startsWith('agent-')
                    };
                })
                .filter(f => f.mtime >= startTime && f.mtime <= endTime && f.size > 0)
                .sort((a, b) => b.mtime - a.mtime);

            return allFiles;
        } catch (error) {
            console.error('Error finding session files:', error.message);
            return [];
        }
    }

    /**
     * v52.0.0: Legacy method for backward compatibility
     */
    findLatestSession(projectDir) {
        const sessions = fs.readdirSync(projectDir)
            .filter(f => f.endsWith('.jsonl'))
            .map(f => ({
                path: path.join(projectDir, f),
                mtime: fs.statSync(path.join(projectDir, f)).mtimeMs
            }))
            .sort((a, b) => b.mtime - a.mtime);

        return sessions.length > 0 ? sessions[0].path : null;
    }

    /**
     * v52.0.0: Categorize files into main sessions and agents
     */
    categorizeSessionFiles(files) {
        const mainSessions = files.filter(f => !f.isAgent);
        const agentSessions = files.filter(f => f.isAgent);

        return {
            primary: mainSessions[0] || null,
            agents: agentSessions,
            manifest: {
                version: '2.0.0',
                capturedAt: new Date().toISOString(),
                distributedCapture: true,
                totalFiles: files.length,
                mainSessionCount: mainSessions.length,
                agentSessionCount: agentSessions.length,
                files: files.map(f => ({
                    filename: f.filename,
                    type: f.isAgent ? 'agent' : 'main',
                    agentId: f.isAgent ? f.filename.replace('agent-', '').replace('.jsonl', '') : null,
                    modifiedAt: new Date(f.mtime).toISOString(),
                    sizeBytes: f.size
                }))
            }
        };
    }

    /**
     * v52.0.0: Extract context from ALL session files and merge
     */
    async extractDistributedContext(allFiles, startTime, endTime) {
        const contexts = [];

        for (const file of allFiles) {
            try {
                const fileContext = await this.parseSessionJSONLWithTimestamps(file.path, startTime, endTime);
                fileContext.sessionType = file.isAgent ? 'agent' : 'primary';
                fileContext.agentId = file.isAgent ? file.filename.replace('agent-', '').replace('.jsonl', '') : null;
                fileContext.filename = file.filename;
                contexts.push(fileContext);
            } catch (error) {
                console.warn(`⚠️  Failed to parse ${file.filename}: ${error.message}`);
            }
        }

        if (contexts.length === 0) {
            return null;
        }

        return this.mergeDistributedContexts(contexts);
    }

    /**
     * v52.0.0: Parse JSONL with explicit timestamp range
     */
    async parseSessionJSONLWithTimestamps(sessionFile, startTime, endTime) {
        const content = fs.readFileSync(sessionFile, 'utf8');
        const lines = content.split('\n').filter(l => l.trim());

        const messages = [];
        const toolCalls = [];
        const fileRefs = new Set();
        let tokenCount = { input: 0, output: 0 };

        for (const line of lines) {
            try {
                const entry = JSON.parse(line);
                const timestamp = new Date(entry.timestamp).getTime();

                // Filter by timeframe
                if (timestamp < startTime || timestamp > endTime) continue;

                // Extract user messages
                if (entry.type === 'user' && entry.message) {
                    const content = entry.message.content || [];
                    for (const item of content) {
                        if (typeof item === 'object' && item.type === 'text') {
                            messages.push({
                                role: 'user',
                                text: item.text || '',
                                timestamp: entry.timestamp
                            });
                        }
                    }
                }

                // Extract assistant responses and tool calls
                if (entry.type === 'assistant' && entry.message) {
                    const content = entry.message.content || [];

                    for (const item of content) {
                        if (typeof item === 'object') {
                            if (item.type === 'text' && item.text) {
                                messages.push({
                                    role: 'assistant',
                                    text: item.text,
                                    timestamp: entry.timestamp
                                });
                            }

                            if (item.type === 'tool_use') {
                                toolCalls.push({
                                    tool: item.name || 'unknown',
                                    input: item.input || {},
                                    timestamp: entry.timestamp
                                });

                                if (item.input && item.input.file_path) {
                                    fileRefs.add(item.input.file_path);
                                }
                            }
                        }
                    }

                    const usage = entry.message.usage || {};
                    tokenCount.input += usage.input_tokens || 0;
                    tokenCount.output += usage.output_tokens || 0;
                }
            } catch (err) {
                continue;
            }
        }

        return {
            messages,
            toolCalls,
            fileRefs: Array.from(fileRefs),
            tokenCount,
            entryCount: lines.length
        };
    }

    /**
     * v52.0.0: Merge contexts from multiple session files
     */
    mergeDistributedContexts(contexts) {
        const merged = {
            messages: [],
            toolCalls: [],
            fileRefs: new Set(),
            tokenCount: { input: 0, output: 0 },
            distributedNodes: [],
            entryCount: 0
        };

        for (const ctx of contexts) {
            // v59.0.0: Merge messages WITH agentId attribution for distributed consciousness
            const messagesWithAgent = ctx.messages.map(msg => ({
                ...msg,
                agentId: ctx.agentId,  // Track which agent/session this message came from
                sessionType: ctx.sessionType  // 'primary' or 'agent'
            }));
            merged.messages.push(...messagesWithAgent);
            merged.toolCalls.push(...ctx.toolCalls);
            ctx.fileRefs.forEach(f => merged.fileRefs.add(f));
            merged.tokenCount.input += ctx.tokenCount.input;
            merged.tokenCount.output += ctx.tokenCount.output;
            merged.entryCount += ctx.entryCount;

            // Track distributed nodes
            merged.distributedNodes.push({
                type: ctx.sessionType,
                agentId: ctx.agentId,
                filename: ctx.filename,
                messageCount: ctx.messages.length,
                toolCallCount: ctx.toolCalls.length,
                tokenCount: ctx.tokenCount.input + ctx.tokenCount.output
            });
        }

        // Sort all messages by timestamp for chronological order
        merged.messages.sort((a, b) =>
            new Date(a.timestamp) - new Date(b.timestamp)
        );

        // Sort tool calls by timestamp
        merged.toolCalls.sort((a, b) =>
            new Date(a.timestamp) - new Date(b.timestamp)
        );

        merged.fileRefs = Array.from(merged.fileRefs);

        return merged;
    }

    /**
     * Legacy method for backward compatibility
     */
    async parseSessionJSONL(sessionFile, minutes) {
        const cutoffTime = Date.now() - (minutes * 60 * 1000);
        return this.parseSessionJSONLWithTimestamps(sessionFile, cutoffTime, Date.now());
    }

    transformForSerializer(sessionData, manifest = null) {
        if (!sessionData) return null;

        const { messages, toolCalls, fileRefs, tokenCount, distributedNodes } = sessionData;

        const userMessages = messages.filter(m => m.role === 'user');
        const assistantMessages = messages.filter(m => m.role === 'assistant');

        const lastUserMessage = userMessages[userMessages.length - 1]?.text || '';

        const workDescription = this.generateWorkDescription(messages, toolCalls, fileRefs);
        const achievements = this.extractAchievements(messages, toolCalls);
        const blockingIssues = this.extractBlockingIssues(messages);
        const nextActions = this.extractNextActions(lastUserMessage, messages);
        const decisions = this.extractDecisions(messages);

        return {
            // For captureActiveContext()
            workDescription,
            currentFocus: lastUserMessage.substring(0, 200) || 'Session work',
            progressMetrics: {
                messagesExchanged: messages.length,
                userMessages: userMessages.length,
                assistantMessages: assistantMessages.length,
                toolsUsed: toolCalls.length,
                filesReferenced: fileRefs.length,
                tokensProcessed: tokenCount.input + tokenCount.output,
                completionStatus: 'Session preserved with full conversation context',
                // v52.0.0: Distributed consciousness metrics
                distributedNodes: distributedNodes ? distributedNodes.length : 1,
                agentSessions: distributedNodes ? distributedNodes.filter(n => n.type === 'agent').length : 0
            },
            blockingIssues,
            nextActions,

            // For buildWorkNarrative()
            sessionStory: workDescription,
            progressArc: this.generateProgressArc(achievements, blockingIssues),
            currentChapter: this.extractCurrentChapter(userMessages),
            nextChapter: nextActions[0] || 'Continue session work',
            achievements,
            challenges: blockingIssues.map(issue => ({
                challenge: issue,
                status: 'identified',
                timestamp: new Date().toISOString()
            })),

            // For archiveDecisionContext()
            decisions,

            // v32.0.0: For user context analyzer
            userMessages: userMessages.map(m => m.text || ''),
            toolUsage: this.extractToolUsage(toolCalls),

            // Full message transcript for dashboard with agent attribution
            messages: messages.map(m => ({
                role: m.role,
                content: m.text || '',
                timestamp: m.timestamp,
                agentId: m.agentId || null,
                sessionType: m.sessionType || 'primary'
            })),

            // v52.0.0: Session manifest for distributed consciousness
            sessionManifest: manifest,
            distributedNodes: distributedNodes || [],

            // Metadata
            extractionMetadata: {
                source: 'claude-code-jsonl',
                version: '2.0.0',
                distributedCapture: manifest ? manifest.distributedCapture : false,
                messageCount: messages.length,
                toolCallCount: toolCalls.length,
                fileRefCount: fileRefs.length,
                nodeCount: distributedNodes ? distributedNodes.length : 1,
                extractionQuality: 'high-fidelity-distributed',
                timestamp: new Date().toISOString()
            }
        };
    }

    generateWorkDescription(messages, toolCalls, fileRefs) {
        const userMessages = messages.filter(m => m.role === 'user');

        let description = '';

        if (userMessages.length > 0) {
            const firstMsg = userMessages[0].text.substring(0, 150);
            const lastMsg = userMessages[userMessages.length - 1].text.substring(0, 150);

            if (userMessages.length === 1) {
                description = firstMsg;
            } else if (userMessages.length === 2) {
                description = `${firstMsg}. Then: ${lastMsg}`;
            } else {
                const midPoint = Math.floor(userMessages.length / 2);
                const midMsg = userMessages[midPoint].text.substring(0, 100);
                description = `Started with: ${firstMsg}. Progressed to: ${midMsg}. Currently: ${lastMsg}`;
            }
        }

        const toolSummary = this.summarizeToolUsage(toolCalls);
        if (toolSummary) {
            description += `. ${toolSummary}`;
        }

        if (fileRefs.length > 0) {
            description += `. Referenced ${fileRefs.length} files`;
        }

        return description.trim();
    }

    summarizeToolUsage(toolCalls) {
        const toolCounts = {};
        toolCalls.forEach(tc => {
            toolCounts[tc.tool] = (toolCounts[tc.tool] || 0) + 1;
        });

        const topTools = Object.entries(toolCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([tool, count]) => `${tool}(${count})`)
            .join(', ');

        return topTools ? `Tools used: ${topTools}` : '';
    }

    extractAchievements(messages, toolCalls) {
        const achievements = [];
        const keywords = ['completed', 'finished', 'done', 'fixed', 'resolved', 'implemented', 'created', 'successfully'];

        messages.forEach(msg => {
            if (msg.role === 'assistant') {
                const lower = msg.text.toLowerCase();
                keywords.forEach(keyword => {
                    if (lower.includes(keyword)) {
                        const sentences = msg.text.split(/[.!?]/);
                        const relevant = sentences.find(s => s.toLowerCase().includes(keyword));
                        if (relevant && relevant.trim().length > 10 && relevant.trim().length < 200) {
                            achievements.push({
                                achievement: relevant.trim(),
                                timestamp: msg.timestamp,
                                type: 'conversation'
                            });
                        }
                    }
                });
            }
        });

        const writeOperations = toolCalls.filter(tc => tc.tool === 'Write' || tc.tool === 'Edit');
        if (writeOperations.length > 0) {
            achievements.push({
                achievement: `Modified/created ${writeOperations.length} files`,
                timestamp: writeOperations[writeOperations.length - 1].timestamp,
                type: 'file_operations'
            });
        }

        const unique = achievements
            .filter((a, i, arr) => arr.findIndex(b => b.achievement === a.achievement) === i)
            .slice(0, 10);

        return unique;
    }

    extractBlockingIssues(messages) {
        const issues = [];
        const keywords = ['error', 'bug', 'issue', 'problem', 'blocker', 'stuck', 'failing', 'broken', 'doesn\'t work'];

        messages.forEach(msg => {
            if (msg.role === 'user') {
                const lower = msg.text.toLowerCase();
                keywords.forEach(keyword => {
                    if (lower.includes(keyword)) {
                        const issue = msg.text.substring(0, 150).trim();
                        if (issue && !issues.includes(issue)) {
                            issues.push(issue);
                        }
                    }
                });
            }
        });

        return issues.slice(0, 5);
    }

    extractNextActions(lastMessage, messages) {
        const actions = [];

        if (lastMessage) {
            actions.push(lastMessage.substring(0, 150));
        }

        const actionKeywords = ['need to', 'should', 'must', 'next', 'will', 'going to', 'plan to', 'implement', 'create'];
        messages.slice(-10).forEach(msg => {
            const lower = msg.text.toLowerCase();
            actionKeywords.forEach(keyword => {
                if (lower.includes(keyword)) {
                    const sentences = msg.text.split(/[.!?]/);
                    const relevant = sentences.find(s => s.toLowerCase().includes(keyword));
                    if (relevant && relevant.trim().length > 10 && relevant.trim().length < 150) {
                        const action = relevant.trim();
                        if (!actions.includes(action)) {
                            actions.push(action);
                        }
                    }
                }
            });
        });

        return actions.slice(0, 5);
    }

    extractDecisions(messages) {
        const decisions = {
            rejectedPaths: [],
            chosenPaths: [],
            tradeOffs: []
        };

        const chooseKeywords = ['will', 'should', 'choose', 'decided', 'going with', 'selected', 'let\'s'];

        messages.slice(-50).forEach(msg => {
            if (msg.role === 'assistant') {
                const lower = msg.text.toLowerCase();

                chooseKeywords.forEach(keyword => {
                    if (lower.includes(keyword)) {
                        const sentences = msg.text.split(/[.!?]/);
                        const relevant = sentences.find(s => s.toLowerCase().includes(keyword));
                        if (relevant && relevant.length > 15 && relevant.length < 200) {
                            decisions.chosenPaths.push({
                                approach: relevant.trim(),
                                rationale: 'Stated in conversation',
                                validation: 'From session discussion',
                                confidence: 0.8
                            });
                        }
                    }
                });
            }
        });

        decisions.chosenPaths = decisions.chosenPaths
            .filter((d, i, arr) => arr.findIndex(x => x.approach === d.approach) === i)
            .slice(0, 3);

        return decisions;
    }

    extractCurrentChapter(userMessages) {
        if (userMessages.length === 0) return 'Session work';

        const lastMessage = userMessages[userMessages.length - 1].text;
        const firstSentence = lastMessage.split(/[.!?]/)[0];
        return firstSentence.substring(0, 100) || 'Current work session';
    }

    extractToolUsage(toolCalls) {
        const toolStats = {};

        toolCalls.forEach(call => {
            const toolName = call.tool || 'unknown';
            if (!toolStats[toolName]) {
                toolStats[toolName] = { name: toolName, count: 0 };
            }
            toolStats[toolName].count++;
        });

        return Object.values(toolStats);
    }

    generateProgressArc(achievements, challenges) {
        const achievementCount = achievements.length;
        const challengeCount = challenges.length;

        if (achievementCount > challengeCount * 2) {
            return 'Strong forward progress with minimal blockers';
        } else if (achievementCount > challengeCount) {
            return 'Steady progress with some challenges addressed';
        } else if (achievementCount === challengeCount) {
            return 'Balanced progress, working through issues';
        } else if (challengeCount > 0) {
            return 'Challenging session with active troubleshooting';
        } else {
            return 'Session in progress';
        }
    }

    /**
     * v52.0.0: Copy original session files to distributed-capture directory
     */
    async preserveOriginalArtifacts(allFiles, outputDir) {
        const captureDir = path.join(outputDir, 'distributed-capture');

        try {
            if (!fs.existsSync(captureDir)) {
                fs.mkdirSync(captureDir, { recursive: true });
            }

            for (const file of allFiles) {
                const destPath = path.join(captureDir, file.filename);
                fs.copyFileSync(file.path, destPath);
            }

            console.log(`📦 Preserved ${allFiles.length} original artifacts in ${captureDir}`);
            return captureDir;
        } catch (error) {
            console.warn(`⚠️  Failed to preserve artifacts: ${error.message}`);
            return null;
        }
    }
}

module.exports = ClaudeCodeContextExtractor;

// CLI Usage
if (require.main === module) {
    const extractor = new ClaudeCodeContextExtractor(process.cwd());
    extractor.extractSessionContext({ sessionDurationMinutes: 120 }).then(context => {
        if (context) {
            console.log('✅ Claude Code context extracted successfully');
            console.log(JSON.stringify(context, null, 2));
        } else {
            console.log('⚠️  No Claude Code context available');
        }
    });
}
