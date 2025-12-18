// COGSPACE v40.0.0
/**
 * COGSPACE v32.0.0 Goal Manager
 * Manages goal hierarchy (ultimate/current/next) for strategic planning
 *
 * @module goal-manager
 * @version 32.0.0
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class GoalManager {
  constructor(projectPath) {
    this.projectPath = projectPath;
    this.goalsDir = path.join(projectPath, 'session-management', 'goals');
    this.ensureGoalsDirectory();
  }

  /**
   * Ensure goals directory exists
   */
  ensureGoalsDirectory() {
    if (!fs.existsSync(this.goalsDir)) {
      fs.mkdirSync(this.goalsDir, { recursive: true });
    }
  }

  /**
   * Create a new goal
   */
  createGoal(goalData) {
    const goal = {
      goalId: this.generateGoalId(),
      goalType: goalData.goalType || 'next',
      title: goalData.title,
      description: goalData.description || '',
      status: 'planning',
      priority: goalData.priority || 'medium',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...goalData
    };

    // Validate required fields
    if (!goal.title) {
      throw new Error('Goal title is required');
    }

    // Set up hierarchy if parent provided
    if (goalData.parentGoalId) {
      goal.hierarchy = {
        parentGoalId: goalData.parentGoalId,
        childGoalIds: [],
        level: this.calculateLevel(goalData.parentGoalId) + 1,
        path: [...this.getGoalPath(goalData.parentGoalId), goal.goalId]
      };

      // Update parent's children
      this.addChildToParent(goalData.parentGoalId, goal.goalId);
    } else {
      goal.hierarchy = {
        parentGoalId: null,
        childGoalIds: [],
        level: 0,
        path: [goal.goalId]
      };
    }

    // Save goal
    this.saveGoal(goal);
    return goal;
  }

  /**
   * Get goal by ID
   */
  getGoal(goalId) {
    const goalPath = path.join(this.goalsDir, `${goalId}.json`);
    if (!fs.existsSync(goalPath)) {
      return null;
    }

    const data = fs.readFileSync(goalPath, 'utf8');
    return JSON.parse(data);
  }

  /**
   * Update goal
   */
  updateGoal(goalId, updates) {
    const goal = this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal ${goalId} not found`);
    }

    const updatedGoal = {
      ...goal,
      ...updates,
      updatedAt: new Date().toISOString()
    };

    // Handle status changes
    if (updates.status === 'completed' && !goal.completedAt) {
      updatedGoal.completedAt = new Date().toISOString();
    }

    this.saveGoal(updatedGoal);
    return updatedGoal;
  }

  /**
   * Update goal progress
   */
  updateProgress(goalId, progressData) {
    const goal = this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal ${goalId} not found`);
    }

    const progress = {
      ...(goal.progress || {}),
      ...progressData,
      lastUpdate: new Date().toISOString()
    };

    // Auto-calculate percentage if tasks provided
    if (progress.tasksCompleted !== undefined && progress.tasksTotal !== undefined) {
      progress.percentage = Math.round((progress.tasksCompleted / progress.tasksTotal) * 100);
    }

    return this.updateGoal(goalId, { progress });
  }

  /**
   * Add success criterion
   */
  addSuccessCriterion(goalId, criterion) {
    const goal = this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal ${goalId} not found`);
    }

    const successCriteria = goal.successCriteria || [];
    successCriteria.push({
      criterion: criterion.criterion,
      type: criterion.type,
      target: criterion.target,
      current: criterion.current,
      achieved: criterion.achieved || false
    });

    return this.updateGoal(goalId, { successCriteria });
  }

  /**
   * Mark criterion as achieved
   */
  achieveCriterion(goalId, criterionIndex) {
    const goal = this.getGoal(goalId);
    if (!goal || !goal.successCriteria || !goal.successCriteria[criterionIndex]) {
      throw new Error('Criterion not found');
    }

    goal.successCriteria[criterionIndex].achieved = true;
    return this.updateGoal(goalId, { successCriteria: goal.successCriteria });
  }

  /**
   * Get all goals
   */
  getAllGoals() {
    if (!fs.existsSync(this.goalsDir)) {
      return [];
    }

    const files = fs.readdirSync(this.goalsDir);
    return files
      .filter(f => f.endsWith('.json'))
      .map(f => {
        const data = fs.readFileSync(path.join(this.goalsDir, f), 'utf8');
        return JSON.parse(data);
      });
  }

  /**
   * Get goals by type
   */
  getGoalsByType(goalType) {
    return this.getAllGoals().filter(g => g.goalType === goalType);
  }

  /**
   * Get goals by status
   */
  getGoalsByStatus(status) {
    return this.getAllGoals().filter(g => g.status === status);
  }

  /**
   * Get active goals (not completed or cancelled)
   */
  getActiveGoals() {
    return this.getAllGoals().filter(g =>
      g.status !== 'completed' && g.status !== 'cancelled'
    );
  }

  /**
   * Get goal hierarchy tree
   */
  getGoalTree() {
    const allGoals = this.getAllGoals();
    const ultimate = allGoals.filter(g => g.goalType === 'ultimate' || g.hierarchy?.level === 0);

    return ultimate.map(root => this.buildTree(root, allGoals));
  }

  /**
   * Build goal tree recursively
   */
  buildTree(goal, allGoals) {
    const children = allGoals.filter(g =>
      g.hierarchy?.parentGoalId === goal.goalId
    );

    return {
      ...goal,
      children: children.map(child => this.buildTree(child, allGoals))
    };
  }

  /**
   * Get current focus goal
   */
  getCurrentGoal() {
    const current = this.getGoalsByType('current').filter(g => g.status === 'active');
    return current.length > 0 ? current[0] : null;
  }

  /**
   * Get ultimate goal
   */
  getUltimateGoal() {
    const ultimate = this.getGoalsByType('ultimate');
    return ultimate.length > 0 ? ultimate[0] : null;
  }

  /**
   * Get next actions (next type goals with high priority)
   */
  getNextActions() {
    return this.getGoalsByType('next')
      .filter(g => g.status === 'active' || g.status === 'planning')
      .sort((a, b) => {
        const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      })
      .slice(0, 5); // Top 5 next actions
  }

  /**
   * Associate session with goal
   */
  addSessionToGoal(goalId, sessionId) {
    const goal = this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal ${goalId} not found`);
    }

    const relatedSessions = goal.relatedSessions || [];
    if (!relatedSessions.includes(sessionId)) {
      relatedSessions.push(sessionId);
    }

    return this.updateGoal(goalId, { relatedSessions });
  }

  /**
   * Generate summary of all goals
   */
  generateGoalSummary() {
    const allGoals = this.getAllGoals();

    const summary = {
      timestamp: new Date().toISOString(),
      total: allGoals.length,
      byType: {},
      byStatus: {},
      byPriority: {},
      ultimate: null,
      current: null,
      nextActions: []
    };

    // Count by type
    ['ultimate', 'current', 'next', 'milestone', 'task'].forEach(type => {
      summary.byType[type] = allGoals.filter(g => g.goalType === type).length;
    });

    // Count by status
    ['planning', 'active', 'paused', 'completed', 'cancelled', 'blocked'].forEach(status => {
      summary.byStatus[status] = allGoals.filter(g => g.status === status).length;
    });

    // Count by priority
    ['critical', 'high', 'medium', 'low'].forEach(priority => {
      summary.byPriority[priority] = allGoals.filter(g => g.priority === priority).length;
    });

    // Get key goals
    summary.ultimate = this.getUltimateGoal();
    summary.current = this.getCurrentGoal();
    summary.nextActions = this.getNextActions();

    return summary;
  }

  /**
   * Private: Generate unique goal ID
   */
  generateGoalId() {
    const timestamp = Date.now();
    const hash = crypto.randomBytes(4).toString('hex');
    return `goal-${timestamp}-${hash}`;
  }

  /**
   * Private: Calculate goal level in hierarchy
   */
  calculateLevel(parentGoalId) {
    if (!parentGoalId) return 0;

    const parent = this.getGoal(parentGoalId);
    return parent ? (parent.hierarchy?.level || 0) : 0;
  }

  /**
   * Private: Get goal path
   */
  getGoalPath(goalId) {
    if (!goalId) return [];

    const goal = this.getGoal(goalId);
    return goal?.hierarchy?.path || [goalId];
  }

  /**
   * Private: Add child to parent goal
   */
  addChildToParent(parentGoalId, childGoalId) {
    const parent = this.getGoal(parentGoalId);
    if (!parent) return;

    const childGoalIds = parent.hierarchy?.childGoalIds || [];
    if (!childGoalIds.includes(childGoalId)) {
      childGoalIds.push(childGoalId);
    }

    parent.hierarchy = {
      ...parent.hierarchy,
      childGoalIds
    };

    this.saveGoal(parent);
  }

  /**
   * Private: Save goal to disk
   */
  saveGoal(goal) {
    const goalPath = path.join(this.goalsDir, `${goal.goalId}.json`);
    fs.writeFileSync(goalPath, JSON.stringify(goal, null, 2));
  }

  /**
   * Delete goal
   */
  deleteGoal(goalId) {
    const goalPath = path.join(this.goalsDir, `${goalId}.json`);
    if (fs.existsSync(goalPath)) {
      // Remove from parent's children
      const goal = this.getGoal(goalId);
      if (goal?.hierarchy?.parentGoalId) {
        const parent = this.getGoal(goal.hierarchy.parentGoalId);
        if (parent) {
          parent.hierarchy.childGoalIds = parent.hierarchy.childGoalIds.filter(id => id !== goalId);
          this.saveGoal(parent);
        }
      }

      fs.unlinkSync(goalPath);
      return true;
    }
    return false;
  }

  /**
   * Archive goal
   */
  archiveGoal(goalId) {
    return this.updateGoal(goalId, {
      'metadata.archived': true,
      'metadata.archivedAt': new Date().toISOString()
    });
  }
}

module.exports = GoalManager;


