import Dexie, { Table } from 'dexie';

export interface AssessmentRecord {
  id?: number;
  username: string;
  assessmentId: string;
  answers: Record<string, number>;
  score: number;
  categoryScores: Record<string, number>;
  completedAt: Date;
  synced: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface JournalRecord {
  id?: number;
  username: string;
  journalId: string;
  content: string;
  mood?: string;
  tags?: string[];
  sentiment?: number;
  createdAt: Date;
  updatedAt: Date;
  synced: boolean;
}

export interface QuestionsCache {
  id?: number;
  age: number;
  language: string;
  questions: any[];
  cachedAt: Date;
  version: string;
}

export interface SyncQueueItem {
  id?: number;
  url: string;
  method: string;
  headers?: Record<string, string>;
  body?: any;
  retryCount: number;
  priority: 'high' | 'medium' | 'low';
  createdAt: Date;
  lastAttempt?: Date;
  error?: string;
}

export interface UserSettings {
  id?: number;
  username: string;
  settings: Record<string, any>;
  synced: boolean;
  updatedAt: Date;
}

export class SoulSenseDB extends Dexie {
  assessments!: Table<AssessmentRecord>;
  journals!: Table<JournalRecord>;
  questionsCache!: Table<QuestionsCache>;
  syncQueue!: Table<SyncQueueItem>;
  userSettings!: Table<UserSettings>;

  constructor() {
    super('SoulSenseDB');

    this.version(1).stores({
      assessments: '++id, username, assessmentId, completedAt, synced, createdAt',
      journals: '++id, username, journalId, createdAt, synced',
      questionsCache: '++id, age, language, cachedAt, version',
      syncQueue: '++id, url, priority, createdAt, retryCount',
      userSettings: '++id, username, synced, updatedAt',
    });
  }

  async clearAllData() {
    await this.transaction('rw', [this.assessments, this.journals, this.questionsCache, this.syncQueue, this.userSettings], async () => {
      await this.assessments.clear();
      await this.journals.clear();
      await this.questionsCache.clear();
      await this.syncQueue.clear();
      await this.userSettings.clear();
    });
  }

  async getPendingAssessments(): Promise<AssessmentRecord[]> {
    return await this.assessments.where('synced').equals(0).toArray();
  }

  async getPendingJournals(): Promise<JournalRecord[]> {
    return await this.journals.where('synced').equals(0).toArray();
  }

  async getSyncQueueItems(priority?: 'high' | 'medium' | 'low'): Promise<SyncQueueItem[]> {
    let query = this.syncQueue.orderBy('priority');

    if (priority) {
      query = this.syncQueue.where('priority').equals(priority);
    }

    return await query.toArray();
  }

  async markAsSynced(table: 'assessments' | 'journals' | 'userSettings', id: number) {
    await this[table].update(id, { synced: true });
  }

  async deleteSyncQueueItem(id: number) {
    await this.syncQueue.delete(id);
  }
}

export const db = new SoulSenseDB();
