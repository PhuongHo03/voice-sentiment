import React from 'react';

interface AdminRefreshButtonProps {
  onClick: () => void;
  isLoading: boolean;
}

export const AdminRefreshButton: React.FC<AdminRefreshButtonProps> = ({ onClick, isLoading }) => {
  return (
    <button className="admin-inline-btn" onClick={onClick} disabled={isLoading}>
      {isLoading ? 'Đang tải...' : 'Làm mới'}
    </button>
  );
};
