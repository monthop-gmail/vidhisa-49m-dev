import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-blue-50 to-slate-100">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-sm p-8 text-center">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">วิทิสา 49 ล้านนาที</h1>
        <p className="text-slate-600">หน้านี้ต้องเข้าผ่าน link ที่สาขาส่งให้</p>
        <p className="text-slate-400 text-sm mt-2">หากได้รับ link จาก Line ของสาขา ให้กด link นั้นเพื่อเข้าใช้งาน</p>
      </div>
    </div>
  )
}
