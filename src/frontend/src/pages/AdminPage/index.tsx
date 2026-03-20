import { NavLink, Outlet } from "react-router-dom";
import { useCustomNavigate } from "@/customization/hooks/use-custom-navigate";
import IconComponent from "../../components/common/genericIconComponent";
import { Button } from "../../components/ui/button";
import { ADMIN_HEADER_TITLE } from "../../constants/constants";

const adminTabs = [
  { label: "Users", path: "/admin/users" },
  { label: "Tenants", path: "/admin/tenants" },
  { label: "System Health", path: "/admin/health" },
];

export default function AdminPage() {
  const navigate = useCustomNavigate();

  return (
    <div className="admin-page-panel flex h-full flex-col pb-8">
      <div className="main-page-nav-arrangement">
        <span className="main-page-nav-title">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <IconComponent name="ChevronLeft" className="w-5" />
          </Button>
          <IconComponent name="Shield" className="w-6" />
          {ADMIN_HEADER_TITLE}
        </span>
      </div>
      <nav className="flex gap-6 border-b border-border bg-background px-1">
        {adminTabs.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path}
            end={tab.path === "/admin/tenants" ? false : undefined}
            className={({ isActive }) =>
              [
                "inline-flex items-center px-1 pb-3 pt-3 text-sm transition-colors",
                isActive
                  ? "border-b-2 border-foreground font-semibold text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              ].join(" ")
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <div className="flex flex-1 flex-col overflow-hidden pt-4">
        <Outlet />
      </div>
    </div>
  );
}
