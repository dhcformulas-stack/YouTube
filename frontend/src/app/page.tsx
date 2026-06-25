import Link from 'next/link';
import Pricing from '@/components/Pricing';

export default function Home() {
  return (
    <div className="bg-gray-50">
      {/* Hero section */}
      <div className="relative isolate overflow-hidden bg-white">
        <div className="mx-auto max-w-7xl px-6 pb-24 pt-10 sm:pb-32 lg:flex lg:px-8 lg:py-40">
          <div className="mx-auto max-w-2xl lg:mx-0 lg:max-w-xl lg:flex-shrink-0 lg:pt-8">
            <h1 className="mt-10 text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Historical & Scientific Accuracy, <span className="text-indigo-600">Forged for You</span>
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              We produce high-quality, 30-minute documentary videos based on your criteria. No creative or editorial work required on your end. Just ready-to-upload assets.
            </p>
            <div className="mt-10 flex items-center gap-x-6">
              <Link
                href="/signup"
                className="rounded-md bg-indigo-600 px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
              >
                Get started
              </Link>
              <Link href="#pricing" className="text-sm font-semibold leading-6 text-gray-900">
                View pricing <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
          <div className="mx-auto mt-16 flex max-w-2xl sm:mt-24 lg:ml-10 lg:mr-0 lg:mt-0 lg:max-w-none lg:flex-none xl:ml-32">
            <div className="max-w-3xl flex-none sm:max-w-5xl lg:max-w-none">
              <div className="rounded-xl bg-gray-900/5 p-2 ring-1 ring-inset ring-gray-900/10 lg:-m-4 lg:rounded-2xl lg:p-4">
                <div className="w-[48rem] rounded-md shadow-2xl ring-1 ring-gray-900/10 h-[24rem] bg-indigo-100 flex items-center justify-center text-indigo-400 font-bold text-2xl border-dashed border-4 border-indigo-200">
                  Documentary Preview Placeholder
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Pricing />
    </div>
  );
}
