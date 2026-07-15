import { createContext, useContext, useState } from "react";

const VaultContext = createContext(null);

export function VaultProvider({ children }) {
    const [entries, setEntries] = useState([]);
    const [isReal, setIsReal] = useState(null);  // null=locked, true=real, false=decoy
    const [unlocked, setUnlocked] = useState(false);

    function lock() {
        setEntries([]);
        setIsReal(null);
        setUnlocked(false);
    }

    return (
        <VaultContext.Provider value={{
            entries, setEntries,
            isReal, setIsReal,
            unlocked, setUnlocked,
            lock
        }}>
            {children}
        </VaultContext.Provider>
    );
}

export const useVault = () => useContext(VaultContext);