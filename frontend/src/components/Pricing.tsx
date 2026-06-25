import Link from 'next/link';

export default function Pricing() {
  const tiers = [
    {
      name: 'Starter',
      price: '$99',
      frequency: '/mo',
      description: 'Perfect for getting started with historical content.',
      features: [
        '1 documentary video per month',
        '30-minute duration',
        'Standard production quality',
        'Historical & scientific accuracy',
        'Ready-to-upload asset',
      ],
      cta: 'Subscribe to Starter',
      mostPopular: false,
    },
    {
      name: 'Intermediate',
      price: '$249.99',
      frequency: '/mo',
      description: 'For growing channels needing more frequent deep dives.',
      features: [
        '2 documentary videos per month',
        '30-minute duration',
        'Priority research & production',
        'Historical & scientific accuracy',
        'Ready-to-upload asset',
        'Priority support',
      ],
      cta: 'Subscribe to Intermediate',
      mostPopular: true,
    },
    {
      name: 'Gold',
      price: '$499.99',
      frequency: '/mo',
      description: 'The ultimate production partner for serious creators.',
      features: [
        '4 documentary videos per month',
        '30-minute duration',
        'Dedicated researcher',
        'Expedited delivery',
        'Premium production quality',
        'Historical & scientific accuracy',
        'Ready-to-upload asset',
      ],
      cta: 'Subscribe to Gold',
      mostPopular: false,
    },
  ];

  return (
    <div id="pricing" className="py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="text-base font-semibold leading-7 text-indigo-600">Pricing</h2>
          <p className="mt-2 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            Choose the right tier for your channel
          </p>
        </div>
        <p className="mx-auto mt-6 max-w-2xl text-center text-lg leading-8 text-gray-600">
          Professional documentaries, fact-checked and produced by experts.
        </p>
        <div className="isolate mx-auto mt-16 grid max-w-md grid-cols-1 gap-y-8 lg:mx-0 lg:max-w-none lg:grid-cols-3 lg:gap-x-8">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`flex flex-col justify-between rounded-3xl bg-white p-8 ring-1 ring-gray-200 xl:p-10 ${
                tier.mostPopular ? 'lg:z-10 lg:scale-105 ring-2 ring-indigo-600' : ''
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-x-4">
                  <h3 id={tier.name} className="text-lg font-semibold leading-8 text-gray-900">
                    {tier.name}
                  </h3>
                  {tier.mostPopular ? (
                    <p className="rounded-full bg-indigo-600/10 px-2.5 py-1 text-xs font-semibold leading-5 text-indigo-600">
                      Most popular
                    </p>
                  ) : null}
                </div>
                <p className="mt-4 text-sm leading-6 text-gray-600">{tier.description}</p>
                <p className="mt-6 flex items-baseline gap-x-1">
                  <span className="text-4xl font-bold tracking-tight text-gray-900">{tier.price}</span>
                  <span className="text-sm font-semibold leading-6 text-gray-600">{tier.frequency}</span>
                </p>
                <ul role="list" className="mt-8 space-x-0 space-y-3 text-sm leading-6 text-gray-600">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex gap-x-3">
                      <svg className="h-6 w-5 flex-none text-indigo-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
              <Link
                href="/signup"
                aria-describedby={tier.name}
                className={`mt-8 block rounded-md px-3 py-2 text-center text-sm font-semibold leading-6 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${
                  tier.mostPopular
                    ? 'bg-indigo-600 text-white shadow-sm hover:bg-indigo-500 focus-visible:outline-indigo-600'
                    : 'text-indigo-600 ring-1 ring-inset ring-indigo-200 hover:ring-indigo-300 focus-visible:outline-indigo-600'
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
