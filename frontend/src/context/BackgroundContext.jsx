// BackgroundContext — lets any child page signal to DashboardLayout
// that the conversation has started, triggering the galaxy fade.
import React, { createContext, useContext, useState } from 'react';

const BackgroundContext = createContext({ hasConversation: false, setHasConversation: () => {} });

export function BackgroundProvider({ children }) {
  const [hasConversation, setHasConversation] = useState(false);
  return (
    <BackgroundContext.Provider value={{ hasConversation, setHasConversation }}>
      {children}
    </BackgroundContext.Provider>
  );
}

export function useBackground() {
  return useContext(BackgroundContext);
}
