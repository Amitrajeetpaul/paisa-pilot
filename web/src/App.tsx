import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AdviseScreen } from './screens/AdviseScreen'
import { AuthScreen } from './screens/AuthScreen'
import { ConfirmScreen } from './screens/ConfirmScreen'
import { ConsentUploadScreen } from './screens/ConsentUploadScreen'
import { DraftsScreen } from './screens/DraftsScreen'
import { FixScreen } from './screens/FixScreen'
import { GstScreen } from './screens/GstScreen'
import { HomeScreen } from './screens/HomeScreen'
import { PrivacyScreen, TermsScreen } from './screens/LegalScreens'
import { LandingScreen } from './screens/LandingScreen'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingScreen />} />
      <Route path="/login" element={<AuthScreen />} />
      <Route path="/privacy" element={<PrivacyScreen />} />
      <Route path="/terms" element={<TermsScreen />} />
      <Route path="/app/consent" element={<ConsentUploadScreen />} />
      <Route path="/app/confirm/:documentType" element={<ConfirmScreen />} />
      <Route path="/app/drafts/:cardId" element={<DraftsScreen />} />
      <Route
        path="/app/home"
        element={
          <AppShell>
            <HomeScreen />
          </AppShell>
        }
      />
      <Route
        path="/app/fix"
        element={
          <AppShell>
            <FixScreen />
          </AppShell>
        }
      />
      <Route
        path="/app/advise"
        element={
          <AppShell>
            <AdviseScreen />
          </AppShell>
        }
      />
      <Route
        path="/app/gst"
        element={
          <AppShell>
            <GstScreen />
          </AppShell>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
