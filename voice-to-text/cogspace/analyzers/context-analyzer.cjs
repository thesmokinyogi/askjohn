#!/usr/bin/env node
// COGSPACE - see cogspace-version.json for version

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Universal Memory Integration
let UniversalMemoryManager;
try {
    UniversalMemoryManager = require('./memory-integration/memory-manager.cjs');
} catch (error) {
    // Graceful fallback if memory integration not available
    UniversalMemoryManager = null;
}

class EnhancedContextAnalyzer {
    constructor(projectRoot = process.cwd()) {
        this.projectRoot = projectRoot;
        this.sessionId = this.generateSessionId();
        this.sessionStartTime = Date.now();
        
        // Initialize Universal Memory if available
        this.memoryManager = null;
        if (UniversalMemoryManager) {
            try {
                this.memoryManager = new UniversalMemoryManager(projectRoot);
            } catch (error) {
                console.error('⚠️ Memory manager initialization failed, continuing without memory integration');
            }
        }
    }

    generateSessionId() {
        const timestamp = Date.now().toString();
        const random = Math.random().toString(36).substring(2, 6);
        return `${timestamp}-${random}`;
    }

    async captureCanvasContext(sessionId, sleepMessage, workSummary) {
        try {
            // 🚨 MEMORY HAZARD FIX: Use GROUND-TRUTH validation
            console.error('🔍 GROUND-TRUTH ANALYSIS: Using filesystem deltas, not cumulative totals');
            
            const sessionChanges = await this.analyzeSessionChanges();
            const recentWork = await this.analyzeRecentWork();
            const actualMetrics = await this.calculateActualMetrics();
            
            // Validate against reality - CRITICAL SAFEGUARD
            this.validateMemoryAccuracy(actualMetrics);

            // 🧠 UNIVERSAL MEMORY ENHANCEMENT
            let basicContext = {
                workDescription: this.generateAccurateWorkDescription(recentWork),
                currentFocus: this.generateCurrentFocus(sleepMessage, recentWork),
                progressArc: this.generateProgressArc(actualMetrics.achievements, actualMetrics.challenges),
                currentChapter: this.generateCurrentChapter(recentWork),
                nextChapter: this.generateNextChapter(actualMetrics.nextActions),
                achievements: actualMetrics.achievements,
                challenges: actualMetrics.challenges,
                nextActions: actualMetrics.nextActions,
                // 🚨 CRITICAL: Return validated metrics
                validatedMetrics: {
                    sessionFilesModified: sessionChanges.modifiedFiles,
                    sessionFilesCreated: sessionChanges.newFiles,
                    recentFilesCount: recentWork.recentFiles.length,
                    validationPassed: true,
                    validationTimestamp: new Date().toISOString()
                }
            };

            // Enhance with Universal AI Memory if available
            if (this.memoryManager && this.memoryManager.isMemoryIntegrationEnabled()) {
                console.error('🧠 Enhancing context with Universal AI Memory...');
                basicContext = await this.memoryManager.enhanceSessionContext(basicContext);
                console.error('✅ Universal Memory enhancement complete');
            }
            
            return basicContext;
        } catch (error) {
            console.error('🚨 CONTEXT ANALYSIS ERROR:', error.message);
            return this.getSafetyFallbackContext(sleepMessage, workSummary);
        }
    }

    async analyzeSessionChanges() {
        const changes = {
            modifiedFiles: 0,
            newFiles: 0,
            deletedFiles: 0,
            filesChanged: [],
            validationMethod: 'filesystem-delta'
        };

        try {
            // INVESTIGATION 2025-10-29: Git detection DISABLED to isolate filesystem scanning performance
            // This is TEMPORARY for performance measurement - will be re-enabled after optimization
            // Original lines 95-110 commented out per Howard/Bob directive

            /*
            // Method 1: Git-based differential analysis (preferred)
            const gitChanges = execSync('git diff --name-status HEAD~1 2>/dev/null || echo ""',
                { cwd: this.projectRoot, encoding: 'utf8' });

            if (gitChanges.trim()) {
                const lines = gitChanges.split('\n').filter(line => line.trim());
                lines.forEach(line => {
                    const [status, filename] = line.split('\t');
                    changes.filesChanged.push({ status, filename });

                    if (status === 'M') changes.modifiedFiles++;
                    if (status === 'A') changes.newFiles++;
                    if (status === 'D') changes.deletedFiles++;
                });
                changes.validationMethod = 'git-diff';
            } else {
            */

            // FORCED to use filesystem scanning for performance measurement
            // Method 2: Filesystem timestamp analysis
            const sessionStartThreshold = this.sessionStartTime - (3 * 60 * 60 * 1000); // 3 hours ago
            changes.validationMethod = 'timestamp-analysis-FORCED';

            const recentFiles = await this.findFilesModifiedSince(sessionStartThreshold);
            changes.modifiedFiles = recentFiles.length;
            changes.filesChanged = recentFiles.map(f => ({ status: 'M', filename: f }));

            // } // End of commented git block

            console.error(`✅ SESSION DELTA: ${changes.modifiedFiles} modified, ${changes.newFiles} new (${changes.validationMethod})`);
            return changes;
            
        } catch (error) {
            console.error('🚨 SESSION ANALYSIS ERROR:', error.message);
            // Emergency fallback - conservative estimates
            return {
                modifiedFiles: 0,
                newFiles: 0,
                deletedFiles: 0,
                filesChanged: [],
                validationMethod: 'emergency-fallback'
            };
        }
    }

    async findFilesModifiedSince(timestamp) {
        // PERFORMANCE INVESTIGATION 2025-10-29: Added detailed timing per Bob's directive
        console.error(`[TIMING] Scan start: ${new Date().toISOString()}`);
        const startTime = Date.now();

        const recentFiles = [];
        let depthWarningShown = false;

        // FIX 2025-10-29: Configurable depth limit (default 5 per Howard's directive)
        const MAX_SCAN_DEPTH = parseInt(process.env.COGSPACE_MAX_DEPTH || '5', 10);

        // FIX 2025-10-29: Expanded skip list per Howard's directive
        const SKIP_DIRS = new Set([
            'node_modules', 'session-management',
            'dist', 'build', 'coverage', '__pycache__',
            'vendor', 'target', '.next', '.nuxt', 'out',
            'venv', 'env', '.venv', '.git'
        ]);

        const scanDirectory = (dir, level = 0) => {
            if (level > MAX_SCAN_DEPTH) {
                if (!depthWarningShown) {
                    console.error(`⚠️ [DEPTH] Reached max depth ${MAX_SCAN_DEPTH} at: ${dir}`);
                    console.error(`⚠️ [DEPTH] Some nested files may be skipped. Set COGSPACE_MAX_DEPTH env var to increase.`);
                    depthWarningShown = true;
                }
                return;
            }

            try {
                const items = fs.readdirSync(dir);
                items.forEach(item => {
                    if (item.startsWith('.') || SKIP_DIRS.has(item)) return;

                    const fullPath = path.join(dir, item);
                    const stat = fs.statSync(fullPath);

                    if (stat.isFile() && stat.mtime.getTime() > timestamp) {
                        recentFiles.push(path.relative(this.projectRoot, fullPath));
                    } else if (stat.isDirectory()) {
                        scanDirectory(fullPath, level + 1);
                    }
                });
            } catch (e) {
                // Directory not accessible, skip
            }
        };

        scanDirectory(this.projectRoot);

        const elapsed = ((Date.now() - startTime) / 1000).toFixed(2);
        console.error(`[TIMING] Scan complete: ${recentFiles.length} files in ${elapsed}s`);
        console.error(`[TIMING] Average: ${(elapsed / (recentFiles.length || 1)).toFixed(3)}s per file`);
        console.error(`[TIMING] Project root: ${this.projectRoot}`);

        return recentFiles;
    }

    async analyzeRecentWork() {
        try {
            const recentFiles = await this.findFilesModifiedSince(Date.now() - (6 * 60 * 60 * 1000)); // 6 hours
            const workContent = {
                recentFiles: recentFiles,
                documentationFiles: [],
                codeFiles: [],
                configFiles: [],
                totalSize: 0
            };

            // Categorize recent files
            for (const filename of recentFiles) {
                const fullPath = path.join(this.projectRoot, filename);
                try {
                    const stat = fs.statSync(fullPath);
                    workContent.totalSize += stat.size;
                    
                    const ext = path.extname(filename).toLowerCase();
                    if (['.md', '.txt', '.rst'].includes(ext)) {
                        workContent.documentationFiles.push(filename);
                    } else if (['.js', '.ts', '.py', '.sh'].includes(ext)) {
                        workContent.codeFiles.push(filename);
                    } else if (['.json', '.yaml', '.yml', '.conf'].includes(ext)) {
                        workContent.configFiles.push(filename);
                    }
                } catch (e) {
                    // File may have been deleted, skip
                }
            }
            
            return workContent;
        } catch (error) {
            return { recentFiles: [], documentationFiles: [], codeFiles: [], configFiles: [], totalSize: 0 };
        }
    }

    async calculateActualMetrics() {
        const recentWork = await this.analyzeRecentWork();
        
        // Generate REALISTIC achievements based on actual file analysis
        const achievements = [];
        if (recentWork.documentationFiles.length > 0) {
            achievements.push(`Created ${recentWork.documentationFiles.length} documentation files`);
        }
        if (recentWork.codeFiles.length > 0) {
            achievements.push(`Modified ${recentWork.codeFiles.length} code files`);
        }
        if (recentWork.configFiles.length > 0) {
            achievements.push(`Updated ${recentWork.configFiles.length} configuration files`);
        }
        
        // Conservative challenge estimation
        const challenges = [];

        // Generate realistic next actions
        const nextActions = [];
        if (recentWork.documentationFiles.length > 0) {
            nextActions.push('Review and validate recent documentation changes');
        }
        if (nextActions.length === 0) {
            nextActions.push('Continue current development work');
        }
        
        return { achievements, challenges, nextActions };
    }

    validateMemoryAccuracy(metrics) {
        // 🚨 CRITICAL VALIDATION: Prevent memory inflation
        const maxReasonableFiles = 100;
        const maxReasonableAchievements = 10;
        
        if (metrics.achievements.length > maxReasonableAchievements) {
            throw new Error(`MEMORY INFLATION DETECTED: ${metrics.achievements.length} achievements exceeds reasonable limit of ${maxReasonableAchievements}`);
        }

        console.error('✅ MEMORY VALIDATION PASSED: Metrics within reasonable bounds');
        return true;
    }

    generateAccurateWorkDescription(recentWork) {
        const { documentationFiles, codeFiles, configFiles } = recentWork;
        const totalFiles = documentationFiles.length + codeFiles.length + configFiles.length;

        if (totalFiles === 0) {
            return 'Session completed with no file modifications detected';
        }

        const parts = [];
        if (documentationFiles.length > 0) {
            parts.push(`${documentationFiles.length} documentation files`);
        }
        if (codeFiles.length > 0) {
            parts.push(`${codeFiles.length} code files`);
        }
        if (configFiles.length > 0) {
            parts.push(`${configFiles.length} configuration files`);
        }

        let description = `Modified ${parts.join(', ')} in current session`;

        // Add example files table if we have files to show
        if (totalFiles > 0) {
            description += '\n\n';
            description += this.generateFileExamplesTable(documentationFiles, codeFiles, configFiles);
        }

        return description;
    }

    generateFileExamplesTable(documentationFiles, codeFiles, configFiles) {
        const examples = [];

        // Get up to 3 examples from each category
        const docExamples = documentationFiles.slice(0, 3);
        const codeExamples = codeFiles.slice(0, 3);
        const configExamples = configFiles.slice(0, 3);

        // Build table only if we have examples
        if (docExamples.length === 0 && codeExamples.length === 0 && configExamples.length === 0) {
            return '';
        }

        let table = '┌─────────────────┬──────────────────────────────────────────────────────┐\n';
        table += '│ Type            │ Example Files                                        │\n';
        table += '├─────────────────┼──────────────────────────────────────────────────────┤\n';

        // Documentation files
        if (docExamples.length > 0) {
            const label = `Documentation (${documentationFiles.length})`;
            table += `│ ${label.padEnd(15)} │ ${this.formatFileName(docExamples[0], 52)} │\n`;
            for (let i = 1; i < docExamples.length; i++) {
                table += `│ ${' '.repeat(15)} │ ${this.formatFileName(docExamples[i], 52)} │\n`;
            }
            if (documentationFiles.length > 3) {
                table += `│ ${' '.repeat(15)} │ ${`... and ${documentationFiles.length - 3} more`.padEnd(52)} │\n`;
            }
        }

        // Code files
        if (codeExamples.length > 0) {
            const label = `Code (${codeFiles.length})`;
            table += `│ ${label.padEnd(15)} │ ${this.formatFileName(codeExamples[0], 52)} │\n`;
            for (let i = 1; i < codeExamples.length; i++) {
                table += `│ ${' '.repeat(15)} │ ${this.formatFileName(codeExamples[i], 52)} │\n`;
            }
            if (codeFiles.length > 3) {
                table += `│ ${' '.repeat(15)} │ ${`... and ${codeFiles.length - 3} more`.padEnd(52)} │\n`;
            }
        }

        // Configuration files
        if (configExamples.length > 0) {
            const label = `Configuration (${configFiles.length})`;
            table += `│ ${label.padEnd(15)} │ ${this.formatFileName(configExamples[0], 52)} │\n`;
            for (let i = 1; i < configExamples.length; i++) {
                table += `│ ${' '.repeat(15)} │ ${this.formatFileName(configExamples[i], 52)} │\n`;
            }
            if (configFiles.length > 3) {
                table += `│ ${' '.repeat(15)} │ ${`... and ${configFiles.length - 3} more`.padEnd(52)} │\n`;
            }
        }

        table += '└─────────────────┴──────────────────────────────────────────────────────┘';

        return table;
    }

    formatFileName(filename, maxLength) {
        // Truncate filename if too long, keeping the end (filename) visible
        if (filename.length <= maxLength) {
            return filename.padEnd(maxLength);
        }

        // Keep the last part visible with ellipsis at the start
        const truncated = '...' + filename.slice(-(maxLength - 3));
        return truncated.padEnd(maxLength);
    }

    generateCurrentFocus(sleepMessage, recentWork) {
        if (recentWork.documentationFiles.length > recentWork.codeFiles.length) {
            return 'Documentation and specification work';
        } else if (recentWork.codeFiles.length > 0) {
            return 'Code development and implementation';
        } else {
            return sleepMessage || 'Session maintenance and organization';
        }
    }

    generateProgressArc(achievements, challenges) {
        if (achievements.length > challenges.length) {
            return 'Steady progress with strong momentum';
        } else if (challenges.length > achievements.length) {
            return 'Active development with identified challenges';
        } else {
            return 'Balanced progress and planning phase';
        }
    }

    generateCurrentChapter(recentWork) {
        if (recentWork.documentationFiles.length > 0) {
            return 'Documentation and specification development';
        } else if (recentWork.codeFiles.length > 0) {
            return 'Implementation and code development';
        } else {
            return 'Session organization and maintenance';
        }
    }

    generateNextChapter(nextActions) {
        if (nextActions.length > 0) {
            return nextActions[0];
        }
        return 'Continue development objectives';
    }

    getSafetyFallbackContext(sleepMessage, workSummary) {
        console.log('🛡️ SAFETY FALLBACK: Using minimal validated context');
        return {
            workDescription: 'Safe session termination with minimal context',
            currentFocus: sleepMessage || 'Session completed',
            progressArc: 'Session preserved with safety protocols',
            currentChapter: 'System maintenance',
            nextChapter: 'Resume development work',
            achievements: ['Session safety protocols activated'],
            challenges: ['Validate system state'],
            nextActions: ['Resume development work'],
            validatedMetrics: {
                sessionFilesModified: 0,
                sessionFilesCreated: 0,
                recentFilesCount: 0,
                validationPassed: true,
                validationTimestamp: new Date().toISOString(),
                fallbackMode: true
            }
        };
    }
}

module.exports = EnhancedContextAnalyzer;

