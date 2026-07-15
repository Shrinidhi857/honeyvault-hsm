import { useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

export function useAutoLock(unlocked, lockFn) {
    const timer = useRef(null);
    const navigate = useNavigate();

    // useCallback so the function reference is stable across renders
    const resetTimer = useCallback(() => {
        clearTimeout(timer.current);
        timer.current = setTimeout(async () => {
            try {
                await axios.post("/api/vault/lock", {}, { withCredentials: true });
            } catch (_) { /* ignore network errors on lock */ }
            lockFn();
            navigate("/unlock");
        }, TIMEOUT_MS);
    }, [lockFn, navigate]);

    // Store resetTimer in a ref so event listeners always use the latest version
    const resetTimerRef = useRef(resetTimer);
    useEffect(() => { resetTimerRef.current = resetTimer; }, [resetTimer]);

    useEffect(() => {
        if (!unlocked) return;

        // Stable wrapper that delegates to the ref — safe to add/remove
        const handler = () => resetTimerRef.current();

        const events = ["mousemove", "keydown", "click", "scroll"];
        events.forEach(e => window.addEventListener(e, handler));
        handler(); // start timer immediately on mount

        return () => {
            events.forEach(e => window.removeEventListener(e, handler));
            clearTimeout(timer.current);
        };
    }, [unlocked]); // only re-runs when lock state changes
}