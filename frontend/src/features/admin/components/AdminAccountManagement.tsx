import React from 'react';
import type { AccountUser } from '../types/admin';
import { AdminRefreshButton } from './AdminRefreshButton';

interface AdminAccountManagementProps {
  accounts: AccountUser[];
  userId?: string;
  pendingCount: number;
  adminCount: number;
  accountsLoading: boolean;
  accountsError: string | null;
  updatingUserId: string | null;
  fetchAccounts: () => void;
  handleToggleStatus: (account: AccountUser) => void;
  handleChangeRole: (account: AccountUser, roleId: string) => void;
}

export const AdminAccountManagement: React.FC<AdminAccountManagementProps> = ({
  accounts,
  userId,
  pendingCount,
  adminCount,
  accountsLoading,
  accountsError,
  updatingUserId,
  fetchAccounts,
  handleToggleStatus,
  handleChangeRole,
}) => {
  const user = { id: userId };

  return (
    <main className="account-mgmt-layout">
    {/* Stats row */}
    <div className="acct-kpi-grid">
      <div className="acct-kpi-card card">
        <span className="kpi-icon">👤</span>
        <div className="kpi-info">
          <h3>Tổng tài khoản</h3>
          <p className="kpi-value">{accounts.length}</p>
        </div>
      </div>
      <div className="acct-kpi-card card">
        <span className="kpi-icon kpi-warn">⏳</span>
        <div className="kpi-info">
          <h3>Chờ kích hoạt</h3>
          <p className="kpi-value kpi-warn">{pendingCount}</p>
        </div>
      </div>
      <div className="acct-kpi-card card">
        <span className="kpi-icon">🛡️</span>
        <div className="kpi-info">
          <h3>Quản trị viên</h3>
          <p className="kpi-value">{adminCount}</p>
        </div>
      </div>
      <div className="acct-kpi-card card">
        <span className="kpi-icon">✅</span>
        <div className="kpi-info">
          <h3>Đang hoạt động</h3>
          <p className="kpi-value kpi-good">{accounts.filter(a => a.is_active).length}</p>
        </div>
      </div>
    </div>

    {/* Accounts table */}
    <div className="account-table-section card">
      <div className="section-header-row">
        <h2>🔐 Quản Lý Tài Khoản Hệ Thống</h2>
        <AdminRefreshButton onClick={fetchAccounts} isLoading={accountsLoading} />
      </div>

      {accountsLoading ? (
        <div className="loader-container"><div className="loader"></div><p>Đang tải danh sách tài khoản...</p></div>
      ) : accountsError ? (
        <div className="auth-error">Lỗi: {accountsError}</div>
      ) : accounts.length === 0 ? (
        <p className="no-data">Chưa có tài khoản nào trong hệ thống.</p>
      ) : (
        <div className="account-table-wrapper">
          <table className="account-table">
            <thead>
              <tr>
                <th>Tài khoản</th>
                <th>Email</th>
                <th>Vai trò</th>
                <th>Ngày tạo</th>
                <th className="text-center">Trạng thái</th>
                <th className="text-center">Kích hoạt</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const ordered = [...accounts];
                const idx = ordered.findIndex(a => a.id === userId);
                if (idx > 0) ordered.unshift(ordered.splice(idx, 1)[0]);
                return ordered.map((acc) => {
                const isSelf = acc.id === user?.id;
                const isUpdating = updatingUserId === acc.id;
                return (
                  <tr key={acc.id} className={`acct-row ${!acc.is_active ? 'inactive-row' : ''} ${isSelf ? 'self-row' : ''}`}>
                    <td>
                      <div className="emp-name-cell">
                        <span className={`emp-avatar ${acc.role_id === 'admin' ? 'admin-avatar' : ''}`}>
                          {acc.username.substring(0, 2).toUpperCase()}
                        </span>
                        <div>
                          <strong>{acc.username}</strong>
                          {isSelf && <span className="self-badge"> (Bạn)</span>}
                        </div>
                      </div>
                    </td>
                    <td className="email-cell">{acc.email}</td>
                    <td>
                      {isSelf ? (
                        <span className={`role-pill ${acc.role_id}`}>{acc.role_id === 'admin' ? '🛡️ Admin' : '👤 Nhân viên'}</span>
                      ) : (
                        <select
                          className={`role-select ${acc.role_id}`}
                          value={acc.role_id}
                          disabled={isUpdating}
                          onChange={(e) => handleChangeRole(acc, e.target.value)}
                        >
                          <option value="employee">👤 Nhân viên</option>
                          <option value="admin">🛡️ Admin</option>
                        </select>
                      )}
                    </td>
                    <td className="date-cell">
                      {new Date(acc.created_at).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })}
                    </td>
                    <td className="text-center">
                      <span className={`status-pill ${acc.is_active ? 'active' : 'inactive'}`}>
                        {acc.is_active ? '✅ Hoạt động' : '⏳ Chờ duyệt'}
                      </span>
                    </td>
                    <td className="text-center">
                      {isSelf ? (
                        <span className="no-action-hint">—</span>
                      ) : (
                        <button
                          className={`toggle-status-btn ${acc.is_active ? 'deactivate' : 'activate'}`}
                          onClick={() => handleToggleStatus(acc)}
                          disabled={isUpdating}
                          title={acc.is_active ? 'Vô hiệu hóa tài khoản' : 'Kích hoạt tài khoản'}
                        >
                          {isUpdating ? (
                            <span className="btn-spinner"></span>
                          ) : acc.is_active ? (
                            '🔒 Vô hiệu hóa'
                          ) : (
                            '🔓 Kích hoạt'
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              });
              })()}
            </tbody>
          </table>
        </div>
      )}
    </div>
  </main>
  );
};
