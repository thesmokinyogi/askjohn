#!/usr/bin/env node
// COGSPACE v40.0.0

class DynamicPriorityEngine {
    constructor() {
        this.fs = require('fs');
        this.path = require('path');
    }

    analyzePriorities(currentContext, sessionHistory) {
        try {
            const realTimePriorities = {
                urgentIssues: this.identifyBlockingProblems(currentContext),
                nextLogicalStep: this.deriveSequentialAction(sessionHistory),
                userIntent: this.parseImplicitObjectives(currentContext),
                contextualRelevance: this.scoreActionRelevance(currentContext)
            };

            return this.prioritizeByImportance(realTimePriorities);
        } catch (error) {
            console.error('Error analyzing priorities:', error.message);
            return this.getFallbackPriorities();
        }
    }

    identifyBlockingProblems(currentContext) {
        const context = currentContext || '';
        const blockingPatterns = [
            /error|failed|broken|critical|emergency/gi,
            /blocked|stuck|cannot|unable|failing/gi,
            /urgent|immediate|asap|priority/gi,
            /alpha tango|delta team|escalate/gi
        ];

        const blockingIssues = [];
        blockingPatterns.forEach(pattern => {
            const matches = context.match(pattern);
            if (matches) {
                blockingIssues.push({
                    type: 'blocking',
                    severity: this.calculateSeverity(matches),
                    context: this.extractBlockingContext(context, matches),
                    priority: 'critical'
                });
            }
        });

        return blockingIssues.slice(0, 5); // Top 5 blocking issues
    }

    calculateSeverity(matches) {
        const severityWeights = {
            'critical': 10, 'emergency': 10, 'alpha tango': 9,
            'failed': 8, 'error': 7, 'broken': 7,
            'blocked': 6, 'urgent': 6, 'stuck': 5
        };

        let totalSeverity = 0;
        matches.forEach(match => {
            const weight = severityWeights[match.toLowerCase()] || 3;
            totalSeverity += weight;
        });

        if (totalSeverity >= 9) return 'critical';
        if (totalSeverity >= 6) return 'high';
        if (totalSeverity >= 3) return 'medium';
        return 'low';
    }

    extractBlockingContext(context, matches) {
        const sentences = context.split(/[.!?]+/);
        const relevantSentences = [];

        matches.forEach(match => {
            sentences.forEach(sentence => {
                if (sentence.toLowerCase().includes(match.toLowerCase()) && sentence.length > 20) {
                    relevantSentences.push(sentence.trim());
                }
            });
        });

        return relevantSentences.slice(0, 3);
    }

    deriveSequentialAction(sessionHistory) {
        const history = sessionHistory || '';
        const actionPatterns = {
            testing: /test|verify|validate|check/gi,
            deployment: /deploy|release|publish|distribute/gi,
            debugging: /debug|fix|repair|troubleshoot/gi,
            development: /implement|create|build|develop/gi,
            analysis: /analyze|review|examine|investigate/gi,
            documentation: /document|write|guide|readme/gi
        };

        const sequentialActions = [];
        Object.keys(actionPatterns).forEach(actionType => {
            const matches = history.match(actionPatterns[actionType]);
            if (matches) {
                sequentialActions.push({
                    type: actionType,
                    frequency: matches.length,
                    nextStep: this.deriveNextStep(actionType, history),
                    confidence: this.calculateConfidence(matches.length, history.length)
                });
            }
        });

        // Sort by frequency and confidence
        return sequentialActions.sort((a, b) => (b.frequency * b.confidence) - (a.frequency * a.confidence));
    }

    deriveNextStep(actionType, history) {
        const nextStepMap = {
            testing: 'Validate test results and fix any failures',
            deployment: 'Monitor deployment and verify functionality',
            debugging: 'Verify fixes and run integration tests',
            development: 'Test implemented features and document changes',
            analysis: 'Document findings and create improvement plan',
            documentation: 'Review documentation accuracy and completeness'
        };

        return nextStepMap[actionType] || 'Continue with next logical workflow step';
    }

    calculateConfidence(frequency, totalLength) {
        const normalizedFreq = Math.min(frequency / 10, 1.0); // Cap at 1.0
        const lengthFactor = Math.min(totalLength / 1000, 1.0); // More content = higher confidence
        return Math.min(normalizedFreq * 0.7 + lengthFactor * 0.3, 1.0);
    }

    parseImplicitObjectives(currentContext) {
        const context = currentContext || '';
        const objectivePatterns = {
            quality: /improve|enhance|optimize|refactor|clean/gi,
            functionality: /add|implement|create|build|develop/gi,
            stability: /fix|repair|resolve|debug|stabilize/gi,
            performance: /speed|fast|optimize|performance|efficient/gi,
            security: /secure|auth|permission|vulnerability|encrypt/gi,
            usability: /user|ux|interface|accessible|intuitive/gi
        };

        const objectives = [];
        Object.keys(objectivePatterns).forEach(objectiveType => {
            const matches = context.match(objectivePatterns[objectiveType]);
            if (matches) {
                objectives.push({
                    type: objectiveType,
                    strength: matches.length,
                    description: this.generateObjectiveDescription(objectiveType, matches),
                    priority: this.calculateObjectivePriority(objectiveType, matches.length)
                });
            }
        });

        return objectives.sort((a, b) => b.strength - a.strength);
    }

    generateObjectiveDescription(objectiveType, matches) {
        const descriptions = {
            quality: `Code quality improvement focusing on ${matches[0] || 'general enhancement'}`,
            functionality: `Feature development for ${matches[0] || 'new capabilities'}`,
            stability: `System stability improvements addressing ${matches[0] || 'current issues'}`,
            performance: `Performance optimization targeting ${matches[0] || 'system efficiency'}`,
            security: `Security enhancements for ${matches[0] || 'system protection'}`,
            usability: `User experience improvements for ${matches[0] || 'interface enhancement'}`
        };

        return descriptions[objectiveType] || `${objectiveType} objective implementation`;
    }

    calculateObjectivePriority(objectiveType, strength) {
        const priorityWeights = {
            stability: 10,    // Fixes are highest priority
            security: 9,      // Security is critical
            functionality: 7,  // New features are important
            performance: 6,   // Optimization is valuable
            quality: 5,       // Quality improvements are good
            usability: 4      // UX improvements are beneficial
        };

        const baseWeight = priorityWeights[objectiveType] || 3;
        const adjustedPriority = baseWeight + Math.min(strength, 5); // Cap strength bonus

        if (adjustedPriority >= 12) return 'critical';
        if (adjustedPriority >= 9) return 'high';
        if (adjustedPriority >= 6) return 'medium';
        return 'low';
    }

    scoreActionRelevance(currentContext) {
        const context = currentContext || '';
        const relevanceFactors = {
            immediacy: this.assessImmediacy(context),
            clarity: this.assessClarity(context),
            completeness: this.assessCompleteness(context),
            feasibility: this.assessFeasibility(context)
        };

        const overallScore = (
            relevanceFactors.immediacy * 0.3 +
            relevanceFactors.clarity * 0.25 +
            relevanceFactors.completeness * 0.25 +
            relevanceFactors.feasibility * 0.2
        );

        return {
            score: overallScore,
            factors: relevanceFactors,
            recommendation: this.generateRelevanceRecommendation(overallScore, relevanceFactors)
        };
    }

    assessImmediacy(context) {
        const immediacyKeywords = ['now', 'immediate', 'urgent', 'asap', 'critical', 'emergency'];
        let score = 0.5; // baseline

        immediacyKeywords.forEach(keyword => {
            if (context.toLowerCase().includes(keyword)) {
                score = Math.min(score + 0.15, 1.0);
            }
        });

        return score;
    }

    assessClarity(context) {
        const clarityIndicators = {
            specific_files: /\w+\.(js|ts|sh|json|md|py|css|html)/gi,
            specific_errors: /error:|failed:|exception:/gi,
            clear_actions: /implement|create|fix|test|deploy/gi,
            measurable_goals: /\d+%|accuracy|complete|finish/gi
        };

        let clarityScore = 0.3; // baseline
        Object.keys(clarityIndicators).forEach(indicator => {
            const matches = context.match(clarityIndicators[indicator]);
            if (matches) {
                clarityScore = Math.min(clarityScore + (matches.length * 0.1), 1.0);
            }
        });

        return clarityScore;
    }

    assessCompleteness(context) {
        const completenessIndicators = [
            'what', 'why', 'how', 'when', 'where',  // W5H framework
            'requirements', 'objectives', 'goals', 'outcomes',
            'steps', 'process', 'workflow', 'sequence'
        ];

        let completenessScore = 0.2; // baseline
        completenessIndicators.forEach(indicator => {
            if (context.toLowerCase().includes(indicator)) {
                completenessScore = Math.min(completenessScore + 0.08, 1.0);
            }
        });

        return completenessScore;
    }

    assessFeasibility(context) {
        const feasibilityFactors = {
            complexity: this.assessComplexity(context),
            resources: this.assessResourceRequirements(context),
            dependencies: this.assessDependencies(context)
        };

        // Higher complexity and dependencies reduce feasibility
        const feasibilityScore = 1.0 - (
            (feasibilityFactors.complexity * 0.4) +
            (feasibilityFactors.resources * 0.3) +
            (feasibilityFactors.dependencies * 0.3)
        );

        return Math.max(feasibilityScore, 0.1); // Minimum feasibility
    }

    assessComplexity(context) {
        const complexityIndicators = [
            'system', 'architecture', 'integration', 'enterprise',
            'multiple', 'complex', 'comprehensive', 'advanced'
        ];

        let complexityScore = 0.2; // baseline
        complexityIndicators.forEach(indicator => {
            if (context.toLowerCase().includes(indicator)) {
                complexityScore = Math.min(complexityScore + 0.15, 1.0);
            }
        });

        return complexityScore;
    }

    assessResourceRequirements(context) {
        const resourceIndicators = [
            'time', 'effort', 'team', 'resources', 'budget',
            'extensive', 'large', 'massive', 'comprehensive'
        ];

        let resourceScore = 0.3; // baseline
        resourceIndicators.forEach(indicator => {
            if (context.toLowerCase().includes(indicator)) {
                resourceScore = Math.min(resourceScore + 0.1, 1.0);
            }
        });

        return resourceScore;
    }

    assessDependencies(context) {
        const dependencyIndicators = [
            'depends', 'requires', 'needs', 'prerequisite',
            'integration', 'coordination', 'approval', 'external'
        ];

        let dependencyScore = 0.2; // baseline
        dependencyIndicators.forEach(indicator => {
            if (context.toLowerCase().includes(indicator)) {
                dependencyScore = Math.min(dependencyScore + 0.12, 1.0);
            }
        });

        return dependencyScore;
    }

    generateRelevanceRecommendation(overallScore, factors) {
        if (overallScore >= 0.8) {
            return 'High relevance - proceed immediately with current priorities';
        } else if (overallScore >= 0.6) {
            return 'Moderate relevance - refine objectives and proceed with caution';
        } else if (overallScore >= 0.4) {
            return 'Low relevance - seek clarification and additional context';
        } else {
            return 'Very low relevance - request detailed requirements and objectives';
        }
    }

    prioritizeByImportance(realTimePriorities) {
        const prioritizedActions = [];

        // Add blocking issues with highest priority
        realTimePriorities.urgentIssues.forEach(issue => {
            prioritizedActions.push({
                action: `Address ${issue.type} issue: ${issue.context[0] || 'System issue'}`,
                priority: 'critical',
                type: 'blocking',
                urgency: 'immediate',
                confidence: 0.9
            });
        });

        // Add sequential actions based on workflow
        realTimePriorities.nextLogicalStep.forEach((step, index) => {
            if (index < 3) { // Top 3 sequential actions
                prioritizedActions.push({
                    action: step.nextStep,
                    priority: this.mapConfidenceToPriority(step.confidence),
                    type: 'sequential',
                    urgency: 'normal',
                    confidence: step.confidence
                });
            }
        });

        // Add objective-based actions
        realTimePriorities.userIntent.forEach((objective, index) => {
            if (index < 2) { // Top 2 objectives
                prioritizedActions.push({
                    action: objective.description,
                    priority: objective.priority,
                    type: 'objective',
                    urgency: 'planned',
                    confidence: Math.min(objective.strength / 10, 1.0)
                });
            }
        });

        // Sort by priority and confidence
        return prioritizedActions.sort((a, b) => {
            const priorityWeight = { critical: 4, high: 3, medium: 2, low: 1 };
            const aPriority = priorityWeight[a.priority] || 1;
            const bPriority = priorityWeight[b.priority] || 1;
            
            if (aPriority !== bPriority) {
                return bPriority - aPriority;
            }
            return b.confidence - a.confidence;
        }).slice(0, 8); // Top 8 prioritized actions
    }

    mapConfidenceToPriority(confidence) {
        if (confidence >= 0.8) return 'high';
        if (confidence >= 0.6) return 'medium';
        return 'low';
    }

    getFallbackPriorities() {
        return [{
            action: 'Continue previous work session',
            priority: 'medium',
            type: 'fallback',
            urgency: 'normal',
            confidence: 0.5
        }];
    }

    // Static method for easy external usage
    static analyzeDynamicPriorities(currentContext, sessionHistory) {
        const engine = new DynamicPriorityEngine();
        return engine.analyzePriorities(currentContext, sessionHistory);
    }
}

module.exports = DynamicPriorityEngine;

