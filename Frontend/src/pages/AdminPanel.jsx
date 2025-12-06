import {
  Activity,
  BarChart3,
  Database,
  HardDrive,
  LogOut,
  Trash2,
  Users,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/ui/Button";
import api from "../services/api";

const AdminPanel = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [activities, setActivities] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAdminData();
  }, [activeTab]);

  const loadAdminData = async () => {
    setLoading(true);
    setError(null);

    try {
      if (activeTab === "overview") {
        const statsRes = await api.apiClient.get("/api/admin/stats");
        const activityRes = await api.apiClient.get("/api/admin/activity");
        setStats(statsRes.data);
        setActivities(activityRes.data.recent_activities);
      } else if (activeTab === "users") {
        const usersRes = await api.apiClient.get("/api/admin/users?limit=100");
        setUsers(usersRes.data.users);
      } else if (activeTab === "datasets") {
        const datasetsRes = await api.apiClient.get(
          "/api/admin/datasets?limit=100"
        );
        setDatasets(datasetsRes.data.datasets);
      }
    } catch (err) {
      console.error("Failed to load admin data:", err);
      setError(err.response?.data?.detail || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (
      !confirm(
        "Are you sure you want to delete this user and all their datasets? This cannot be undone."
      )
    ) {
      return;
    }

    try {
      await api.apiClient.delete(`/api/admin/users/${userId}`);
      setUsers(users.filter((u) => u.id !== userId));
      alert("User deleted successfully");
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to delete user");
    }
  };

  const handleDeleteDataset = async (datasetId) => {
    if (!confirm("Are you sure you want to delete this dataset?")) {
      return;
    }

    try {
      await api.apiClient.delete(`/api/admin/datasets/${datasetId}`);
      setDatasets(datasets.filter((d) => d.id !== datasetId));
      alert("Dataset deleted successfully");
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to delete dataset");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("astropixel_token");
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Top Navigation */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">🛡️ Admin Panel</h1>
          <Button
            variant="ghost"
            onClick={handleLogout}
            className="gap-2 text-gray-400 hover:text-white"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </Button>
        </div>
      </nav>

      {/* Tabs */}
      <div className="bg-gray-900 border-b border-gray-800 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-8">
            {[
              { id: "overview", label: "Overview", icon: BarChart3 },
              { id: "users", label: "Users", icon: Users },
              { id: "datasets", label: "Datasets", icon: Database },
              { id: "activity", label: "Activity", icon: Activity },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`px-4 py-4 border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === id
                    ? "border-blue-500 text-white"
                    : "border-transparent text-gray-400 hover:text-gray-300"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400">
            {error}
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {activeTab === "overview" && (
              <div className="space-y-8">
                {/* Statistics Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    {
                      label: "Total Users",
                      value: stats?.users.total,
                      icon: Users,
                      color: "blue",
                    },
                    {
                      label: "Total Datasets",
                      value: stats?.datasets.total,
                      icon: Database,
                      color: "green",
                    },
                    {
                      label: "Demo Datasets",
                      value: stats?.datasets.demo,
                      icon: Database,
                      color: "purple",
                    },
                    {
                      label: "Storage Used",
                      value: `${stats?.storage.total_gb} GB`,
                      icon: HardDrive,
                      color: "orange",
                    },
                  ].map((stat, idx) => {
                    const Icon = stat.icon;
                    const colorClasses = {
                      blue: "bg-blue-500/10 border-blue-500/30 text-blue-400",
                      green:
                        "bg-green-500/10 border-green-500/30 text-green-400",
                      purple:
                        "bg-purple-500/10 border-purple-500/30 text-purple-400",
                      orange:
                        "bg-orange-500/10 border-orange-500/30 text-orange-400",
                    };

                    return (
                      <div
                        key={idx}
                        className={`border rounded-lg p-6 ${
                          colorClasses[stat.color]
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium opacity-75">
                              {stat.label}
                            </p>
                            <p className="text-3xl font-bold mt-2">
                              {stat.value}
                            </p>
                          </div>
                          <Icon className="w-12 h-12 opacity-50" />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Detailed Statistics */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Dataset Statistics */}
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">
                      📊 Dataset Statistics
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Completed</span>
                        <span className="text-white font-semibold">
                          {stats?.datasets.completed}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Processing</span>
                        <span className="text-yellow-400 font-semibold">
                          {stats?.datasets.processing}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Failed</span>
                        <span className="text-red-400 font-semibold">
                          {stats?.datasets.failed}
                        </span>
                      </div>
                      <div className="border-t border-gray-700 pt-3 mt-3">
                        <div className="flex justify-between">
                          <span className="text-gray-400">
                            Avg Dataset Size
                          </span>
                          <span className="text-white font-semibold">
                            {stats?.storage.avg_dataset_mp} MP
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* User Statistics */}
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">
                      👥 User Statistics
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Total Users</span>
                        <span className="text-white font-semibold">
                          {stats?.users.total}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Created Today</span>
                        <span className="text-green-400 font-semibold">
                          {stats?.users.created_today}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">User Uploads</span>
                        <span className="text-white font-semibold">
                          {stats?.datasets.user_uploads}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Users Tab */}
            {activeTab === "users" && (
              <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Email
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Username
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Datasets
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Storage (MB)
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Joined
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {users.map((user) => (
                      <tr key={user.id} className="hover:bg-gray-800/50">
                        <td className="px-6 py-4 text-sm text-white">
                          {user.email}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {user.username}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {user.datasets_count}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {user.storage_mb}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <button
                            onClick={() => handleDeleteUser(user.id)}
                            className="text-red-400 hover:text-red-300 gap-1 flex items-center"
                          >
                            <Trash2 className="w-4 h-4" />
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {users.length === 0 && (
                  <div className="p-8 text-center text-gray-400">
                    No users found
                  </div>
                )}
              </div>
            )}

            {/* Datasets Tab */}
            {activeTab === "datasets" && (
              <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Name
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Owner
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Size (MP)
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Status
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Type
                      </th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {datasets.map((dataset) => (
                      <tr key={dataset.id} className="hover:bg-gray-800/50">
                        <td className="px-6 py-4 text-sm text-white">
                          {dataset.name}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {dataset.owner_email}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {dataset.size_mp}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              dataset.processing_status === "completed"
                                ? "bg-green-500/20 text-green-400"
                                : dataset.processing_status === "processing"
                                ? "bg-yellow-500/20 text-yellow-400"
                                : "bg-red-500/20 text-red-400"
                            }`}
                          >
                            {dataset.processing_status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {dataset.is_demo ? (
                            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs">
                              DEMO
                            </span>
                          ) : (
                            <span className="text-gray-400">User Upload</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <button
                            onClick={() => handleDeleteDataset(dataset.id)}
                            className="text-red-400 hover:text-red-300 gap-1 flex items-center"
                          >
                            <Trash2 className="w-4 h-4" />
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {datasets.length === 0 && (
                  <div className="p-8 text-center text-gray-400">
                    No datasets found
                  </div>
                )}
              </div>
            )}

            {/* Activity Tab */}
            {activeTab === "activity" && (
              <div className="space-y-4">
                {activities.map((activity, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-900 border border-gray-800 rounded-lg p-4"
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className={`w-2 h-2 rounded-full mt-2 ${
                          activity.type === "dataset_created"
                            ? "bg-blue-400"
                            : "bg-green-400"
                        }`}
                      />
                      <div className="flex-1">
                        <p className="text-white font-medium">
                          {activity.type === "dataset_created"
                            ? `Dataset "${activity.name}" created`
                            : `User "${activity.email}" signed up`}
                        </p>
                        <p className="text-sm text-gray-400 mt-1">
                          {activity.type === "dataset_created" &&
                            `Owner: ${activity.owner} | Status: ${activity.status}`}
                        </p>
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(activity.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AdminPanel;
