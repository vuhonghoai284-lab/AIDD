import React, { useState, useMemo } from 'react';
import { Select, Avatar, Spin, Empty } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { debounce } from 'lodash';

interface User {
  id: number;
  uid: string;
  display_name: string;
  avatar_url?: string;
  is_admin: boolean;
  is_system_admin: boolean;
}

interface UserSearchSelectProps {
  value?: number[];
  onChange?: (value: number[]) => void;
  placeholder?: string;
  maxCount?: number;
  disabled?: boolean;
}

export const UserSearchSelect: React.FC<UserSearchSelectProps> = ({
  value = [],
  onChange,
  placeholder = "搜索用户名、显示名称或邮箱",
  maxCount = 20,
  disabled = false
}) => {
  const [searchValue, setSearchValue] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedUsers, setSelectedUsers] = useState<User[]>([]);

  // 防抖搜索函数
  const debouncedSearch = useMemo(
    () => debounce(async (searchTerm: string) => {
      if (!searchTerm || searchTerm.length < 2) {
        setUsers([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const response = await fetch(
          `/api/task-share/users/search?q=${encodeURIComponent(searchTerm)}&limit=50`,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          }
        );

        if (response.ok) {
          const searchResults = await response.json();
          setUsers(searchResults);
        } else {
          console.error('用户搜索失败:', response.statusText);
          setUsers([]);
        }
      } catch (error) {
        console.error('用户搜索出错:', error);
        setUsers([]);
      } finally {
        setLoading(false);
      }
    }, 300),
    []
  );

  const handleSearch = (searchTerm: string) => {
    setSearchValue(searchTerm);
    debouncedSearch(searchTerm);
  };

  const handleChange = (selectedIds: number[]) => {
    // 更新选中的用户
    const newSelectedUsers = users.filter(user => selectedIds.includes(user.id));
    // 保留之前已选中但不在当前搜索结果中的用户
    const previouslySelected = selectedUsers.filter(user => 
      !users.find(u => u.id === user.id) && selectedIds.includes(user.id)
    );
    
    setSelectedUsers([...newSelectedUsers, ...previouslySelected]);
    onChange?.(selectedIds);
  };

  const renderOption = (user: User) => (
    <Select.Option key={user.id} value={user.id}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Avatar 
          size={24} 
          src={user.avatar_url} 
          icon={<UserOutlined />}
        />
        <div>
          <div style={{ fontWeight: 500 }}>{user.display_name}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            @{user.uid}
            {(user.is_admin || user.is_system_admin) && (
              <span style={{ marginLeft: 4, color: '#1890ff' }}>
                (管理员)
              </span>
            )}
          </div>
        </div>
      </div>
    </Select.Option>
  );

  const renderSelectedItem = (userId: number) => {
    const user = selectedUsers.find(u => u.id === userId) || 
                 users.find(u => u.id === userId);
    
    if (!user) return userId;
    
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <Avatar size={16} src={user.avatar_url} icon={<UserOutlined />} />
        <span>{user.display_name}</span>
      </div>
    );
  };

  return (
    <Select
      mode="multiple"
      showSearch
      value={value}
      placeholder={placeholder}
      defaultActiveFirstOption={false}
      showArrow={false}
      filterOption={false}
      onSearch={handleSearch}
      onChange={handleChange}
      notFoundContent={
        loading ? (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Spin size="small" />
            <div style={{ marginTop: 8 }}>搜索中...</div>
          </div>
        ) : searchValue && searchValue.length >= 2 ? (
          <Empty 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="未找到匹配用户"
            style={{ padding: 16 }}
          />
        ) : searchValue ? (
          <div style={{ textAlign: 'center', padding: 16, color: '#999' }}>
            请输入至少2个字符进行搜索
          </div>
        ) : null
      }
      tagRender={({ value: userId, onClose }) => (
        <span 
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '2px 8px',
            backgroundColor: '#f0f0f0',
            borderRadius: 4,
            fontSize: '12px',
            maxWidth: 120,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}
        >
          {renderSelectedItem(userId)}
          <span 
            onClick={onClose}
            style={{ 
              marginLeft: 4, 
              cursor: 'pointer',
              fontSize: '10px',
              color: '#999'
            }}
          >
            ×
          </span>
        </span>
      )}
      maxCount={maxCount}
      disabled={disabled}
      style={{ width: '100%' }}
    >
      {users.map(renderOption)}
    </Select>
  );
};