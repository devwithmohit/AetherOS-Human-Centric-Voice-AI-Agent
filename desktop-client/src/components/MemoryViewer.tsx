import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@store/appStore';

interface MemoryViewerProps {
  userId?: string;
  onDeleteMemory?: (id: string) => void;
  onEditPreference?: (id: string, newValue: string) => void;
}

type TabType = 'recent' | 'preferences' | 'episodic';

export const MemoryViewer: React.FC<MemoryViewerProps> = ({
  userId,
  onDeleteMemory,
  onEditPreference,
}) => {
  const memories = useAppStore((state) => state.memories);
  const messages = useAppStore((state) => state.messages);
  const removeMemory = useAppStore((state) => state.removeMemory);

  const [activeTab, setActiveTab] = useState<TabType>('recent');
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  // Recent Context: Last 10 conversation turns
  const recentContext = messages.slice(-10);

  // Preferences: Learned habits (editable)
  const preferences = memories.filter((m) => m.type === 'preference');

  // Episodic: Past interactions (searchable)
  const episodicMemories = memories.filter(
    (m) => m.type === 'fact' || m.type === 'context'
  );
  const filteredEpisodic = searchQuery
    ? episodicMemories.filter((m) =>
        m.content.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : episodicMemories;

  const handleDelete = (id: string) => {
    removeMemory(id);
    if (onDeleteMemory) {
      onDeleteMemory(id);
    }
  };

  const handleEdit = (id: string, currentValue: string) => {
    setEditingId(id);
    setEditValue(currentValue);
  };

  const handleSaveEdit = (id: string) => {
    if (onEditPreference) {
      onEditPreference(id, editValue);
    }
    setEditingId(null);
    setEditValue('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditValue('');
  };

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'fact':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'preference':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      case 'context':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-slate-800 to-slate-700 border-b border-slate-600">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-white font-semibold flex items-center gap-2">
              <svg className="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Memory Dashboard
            </h2>
            <p className="text-xs text-slate-400">Transparency into what Aether remembers</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('recent')}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              activeTab === 'recent'
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            Recent Context
            {recentContext.length > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-slate-900/50 rounded text-xs">
                {recentContext.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('preferences')}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              activeTab === 'preferences'
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            Preferences
            {preferences.length > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-slate-900/50 rounded text-xs">
                {preferences.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('episodic')}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              activeTab === 'episodic'
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            Episodic
            {episodicMemories.length > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-slate-900/50 rounded text-xs">
                {episodicMemories.length}
              </span>
            )}
          </button>
        </div>

        {/* Search bar for episodic tab */}
        {activeTab === 'episodic' && (
          <div className="mt-3">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search memories..."
                className="w-full px-4 py-2 pl-10 bg-slate-800 text-white rounded-lg border border-slate-700 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 text-sm"
              />
              <svg
                className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
        )}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-800">
        <AnimatePresence mode="wait">
          {/* Recent Context Tab */}
          {activeTab === 'recent' && (
            <motion.div
              key="recent"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {recentContext.length === 0 ? (
                <EmptyState message="No recent conversations yet. Start chatting to see context." />
              ) : (
                recentContext.map((msg, index) => (
                  <div
                    key={msg.id}
                    className="bg-slate-800 rounded-lg p-4 border border-slate-700"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        msg.role === 'user'
                          ? 'bg-slate-600'
                          : 'bg-gradient-to-br from-primary-500 to-accent-500'
                      }`}>
                        <span className="text-white text-xs font-semibold">
                          {msg.role === 'user' ? 'U' : 'A'}
                        </span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-slate-400 capitalize">
                            {msg.role}
                          </span>
                          <span className="text-xs text-slate-600">•</span>
                          <span className="text-xs text-slate-500">
                            {formatDate(msg.timestamp)}
                          </span>
                        </div>
                        <p className="text-sm text-slate-200 leading-relaxed">
                          {msg.content.substring(0, 200)}
                          {msg.content.length > 200 && '...'}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}

          {/* Preferences Tab */}
          {activeTab === 'preferences' && (
            <motion.div
              key="preferences"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {preferences.length === 0 ? (
                <EmptyState message="No preferences learned yet. Keep chatting to help Aether understand you better." />
              ) : (
                preferences.map((pref) => (
                  <div
                    key={pref.id}
                    className="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:border-purple-500/30 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                          </svg>
                          <span className="text-xs font-medium text-purple-400">Preference</span>
                        </div>

                        {editingId === pref.id ? (
                          <div className="space-y-2">
                            <textarea
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              className="w-full px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20 text-sm"
                              rows={3}
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleSaveEdit(pref.id)}
                                className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white rounded text-xs transition-colors"
                              >
                                Save
                              </button>
                              <button
                                onClick={handleCancelEdit}
                                className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-xs transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <p className="text-sm text-slate-200 leading-relaxed mb-2">
                              {pref.content}
                            </p>
                            <div className="flex items-center gap-3 text-xs text-slate-500">
                              <span>{formatDate(pref.timestamp)}</span>
                              {pref.source && (
                                <>
                                  <span>•</span>
                                  <span>{pref.source}</span>
                                </>
                              )}
                            </div>
                          </>
                        )}
                      </div>

                      {editingId !== pref.id && (
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleEdit(pref.id, pref.content)}
                            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                            title="Edit preference"
                          >
                            <svg className="w-4 h-4 text-slate-400 hover:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDelete(pref.id)}
                            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                            title="Remove preference"
                          >
                            <svg className="w-4 h-4 text-slate-400 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}

          {/* Episodic Tab */}
          {activeTab === 'episodic' && (
            <motion.div
              key="episodic"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-3"
            >
              {filteredEpisodic.length === 0 ? (
                <EmptyState
                  message={
                    searchQuery
                      ? `No memories found matching "${searchQuery}"`
                      : 'No episodic memories yet. Facts and context will appear here.'
                  }
                />
              ) : (
                filteredEpisodic.map((memory) => (
                  <div
                    key={memory.id}
                    className="bg-slate-800 rounded-lg p-4 border border-slate-700 hover:border-slate-600 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs border mb-2 ${getTypeColor(memory.type)}`}>
                          <span className="capitalize">{memory.type}</span>
                        </div>

                        <p className="text-sm text-slate-200 leading-relaxed mb-2">
                          {memory.content}
                        </p>

                        <div className="flex items-center gap-3 text-xs text-slate-500">
                          <span>{formatDate(memory.timestamp)}</span>
                          {memory.source && (
                            <>
                              <span>•</span>
                              <span>{memory.source}</span>
                            </>
                          )}
                        </div>
                      </div>

                      <button
                        onClick={() => handleDelete(memory.id)}
                        className="opacity-0 group-hover:opacity-100 p-2 hover:bg-slate-700 rounded-lg transition-all"
                        title="Remove memory"
                      >
                        <svg className="w-4 h-4 text-slate-400 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

const EmptyState: React.FC<{ message: string }> = ({ message }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-12">
      <div className="w-16 h-16 mb-3 rounded-full bg-slate-800 flex items-center justify-center">
        <svg className="w-8 h-8 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
      </div>
      <p className="text-sm text-slate-500 max-w-sm">{message}</p>
    </div>
  );
};
//                     </div>
//                   </div>

//                   {/* Delete button */}
//                   <button
//                     onClick={() => removeMemory(memory.id)}
//                     className="opacity-0 group-hover:opacity-100 p-2 hover:bg-slate-700 rounded-lg transition-all"
//                     title="Remove memory"
//                   >
//                     <svg className="w-4 h-4 text-slate-400 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
//                       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
//                     </svg>
//                   </button>
//                 </div>
//               </motion.div>
//             ))
//           )}
//         </AnimatePresence>
//       </div>
//     </div>
//   );
// };
