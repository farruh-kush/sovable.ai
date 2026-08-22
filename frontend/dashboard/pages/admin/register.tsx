import PortalAuthCard from '../../components/PortalAuthCard'

export default function AdminPortalRegister() {
  return <PortalAuthCard mode="register" accountType="admin" eyebrow="ADMIN PORTAL / REGISTER" title="Create an organization-admin account" successHref="/admin" />
}
