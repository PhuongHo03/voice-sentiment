interface AuthMessageProps {
  type: 'error' | 'success';
  message: string;
  onClose: () => void;
}

export function AuthMessage({ type, message, onClose }: AuthMessageProps) {
  return (
    <div className={type === 'error' ? 'auth-error' : 'auth-success'}>
      <span>{message}</span>
      <button type="button" onClick={onClose} className="error-close-btn">&times;</button>
    </div>
  );
}
