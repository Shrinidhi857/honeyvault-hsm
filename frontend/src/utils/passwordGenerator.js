/**
 * passwordGenerator.js
 * Generates strong random passwords with configurable options.
 */

const LOWERCASE = 'abcdefghijklmnopqrstuvwxyz';
const UPPERCASE = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const DIGITS = '0123456789';
const SYMBOLS = '!@#$%^&*()_+-=[]{}|;:,.<>?';

export function generatePassword({
    length = 16,
    upper = true,
    digits = true,
    symbols = true,
} = {}) {
    let charset = LOWERCASE;
    const required = [LOWERCASE[Math.floor(Math.random() * LOWERCASE.length)]];

    if (upper) { charset += UPPERCASE; required.push(UPPERCASE[Math.floor(Math.random() * UPPERCASE.length)]); }
    if (digits) { charset += DIGITS; required.push(DIGITS[Math.floor(Math.random() * DIGITS.length)]); }
    if (symbols) { charset += SYMBOLS; required.push(SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]); }

    // Fill remaining length with random chars from full charset
    const rest = Array.from(
        { length: length - required.length },
        () => charset[Math.floor(Math.random() * charset.length)]
    );

    // Shuffle required + rest together
    const all = [...required, ...rest];
    for (let i = all.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [all[i], all[j]] = [all[j], all[i]];
    }

    return all.join('');
}

export function getStrength(password) {
    let score = 0;
    const checks = {
        length8: password.length >= 8,
        length12: password.length >= 12,
        length16: password.length >= 16,
        hasLower: /[a-z]/.test(password),
        hasUpper: /[A-Z]/.test(password),
        hasDigit: /[0-9]/.test(password),
        hasSymbol: /[^a-zA-Z0-9]/.test(password),
        noCommon: !['password', '123456', 'qwerty', 'letmein', 'admin'].includes(password.toLowerCase()),
    };

    score = Object.values(checks).filter(Boolean).length;

    if (score <= 3) return { label: 'Weak', color: '#ef4444', width: '25%' };
    if (score <= 5) return { label: 'Fair', color: '#eab308', width: '50%' };
    if (score <= 7) return { label: 'Strong', color: '#22c55e', width: '75%' };
    return { label: 'Very Strong', color: '#7c6ff7', width: '100%' };
}