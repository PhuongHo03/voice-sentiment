import React from 'react';
import type { ToastMessage } from '../states/adminState';

interface AdminToastProps {
  toastMessage: ToastMessage | null;
}

export const AdminToast: React.FC<AdminToastProps> = ({ toastMessage }) => {
  if (!toastMessage) return null;

  return (
    <div className={`admin-toast ${toastMessage.type}`}>
      <span>{toastMessage.type === 'success' ? '✅' : '❌'}</span>
      <span>{toastMessage.text}</span>
    </div>
  );
};
