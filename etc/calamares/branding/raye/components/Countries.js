// Countries and regions of the region page, with their time zones. The
// first zone of a country is the one picked when nothing better is known;
// countries with several get a second list. A country missing here can
// still be set with "My country isn't listed" (every time zone).
.pragma library

var list = [
    { code: "AL", en: "Albania", fr: "Albanie", zones: [["Europe/Tirane"]] },
    { code: "AD", en: "Andorra", fr: "Andorre", zones: [["Europe/Andorra"]] },
    { code: "AM", en: "Armenia", fr: "Arménie", zones: [["Asia/Yerevan"]] },
    { code: "AZ", en: "Azerbaijan", fr: "Azerbaïdjan", zones: [["Asia/Baku"]] },
    { code: "BD", en: "Bangladesh", fr: "Bangladesh", zones: [["Asia/Dhaka"]] },
    { code: "BY", en: "Belarus", fr: "Biélorussie", zones: [["Europe/Minsk"]] },
    { code: "BO", en: "Bolivia", fr: "Bolivie", zones: [["America/La_Paz"]] },
    { code: "BA", en: "Bosnia and Herzegovina", fr: "Bosnie-Herzégovine", zones: [["Europe/Sarajevo"]] },
    { code: "BG", en: "Bulgaria", fr: "Bulgarie", zones: [["Europe/Sofia"]] },
    { code: "CR", en: "Costa Rica", fr: "Costa Rica", zones: [["America/Costa_Rica"]] },
    { code: "HR", en: "Croatia", fr: "Croatie", zones: [["Europe/Zagreb"]] },
    { code: "CU", en: "Cuba", fr: "Cuba", zones: [["America/Havana"]] },
    { code: "CY", en: "Cyprus", fr: "Chypre", zones: [["Asia/Nicosia"]] },
    { code: "DO", en: "Dominican Republic", fr: "République dominicaine", zones: [["America/Santo_Domingo"]] },
    { code: "EC", en: "Ecuador", fr: "Équateur", zones: [["America/Guayaquil"]] },
    { code: "SV", en: "El Salvador", fr: "Salvador", zones: [["America/El_Salvador"]] },
    { code: "EE", en: "Estonia", fr: "Estonie", zones: [["Europe/Tallinn"]] },
    { code: "ET", en: "Ethiopia", fr: "Éthiopie", zones: [["Africa/Addis_Ababa"]] },
    { code: "GE", en: "Georgia", fr: "Géorgie", zones: [["Asia/Tbilisi"]] },
    { code: "GH", en: "Ghana", fr: "Ghana", zones: [["Africa/Accra"]] },
    { code: "GT", en: "Guatemala", fr: "Guatemala", zones: [["America/Guatemala"]] },
    { code: "HN", en: "Honduras", fr: "Honduras", zones: [["America/Tegucigalpa"]] },
    { code: "HK", en: "Hong Kong", fr: "Hong Kong", zones: [["Asia/Hong_Kong"]] },
    { code: "IS", en: "Iceland", fr: "Islande", zones: [["Atlantic/Reykjavik"]] },
    { code: "IR", en: "Iran", fr: "Iran", zones: [["Asia/Tehran"]] },
    { code: "IQ", en: "Iraq", fr: "Irak", zones: [["Asia/Baghdad"]] },
    { code: "JO", en: "Jordan", fr: "Jordanie", zones: [["Asia/Amman"]] },
    { code: "KE", en: "Kenya", fr: "Kenya", zones: [["Africa/Nairobi"]] },
    { code: "KW", en: "Kuwait", fr: "Koweït", zones: [["Asia/Kuwait"]] },
    { code: "LV", en: "Latvia", fr: "Lettonie", zones: [["Europe/Riga"]] },
    { code: "LT", en: "Lithuania", fr: "Lituanie", zones: [["Europe/Vilnius"]] },
    { code: "MY", en: "Malaysia", fr: "Malaisie", zones: [["Asia/Kuala_Lumpur"]] },
    { code: "MT", en: "Malta", fr: "Malte", zones: [["Europe/Malta"]] },
    { code: "MD", en: "Moldova", fr: "Moldavie", zones: [["Europe/Chisinau"]] },
    { code: "ME", en: "Montenegro", fr: "Monténégro", zones: [["Europe/Podgorica"]] },
    { code: "NP", en: "Nepal", fr: "Népal", zones: [["Asia/Kathmandu"]] },
    { code: "NI", en: "Nicaragua", fr: "Nicaragua", zones: [["America/Managua"]] },
    { code: "MK", en: "North Macedonia", fr: "Macédoine du Nord", zones: [["Europe/Skopje"]] },
    { code: "OM", en: "Oman", fr: "Oman", zones: [["Asia/Muscat"]] },
    { code: "PK", en: "Pakistan", fr: "Pakistan", zones: [["Asia/Karachi"]] },
    { code: "PA", en: "Panama", fr: "Panama", zones: [["America/Panama"]] },
    { code: "PY", en: "Paraguay", fr: "Paraguay", zones: [["America/Asuncion"]] },
    { code: "PR", en: "Puerto Rico", fr: "Porto Rico", zones: [["America/Puerto_Rico"]] },
    { code: "QA", en: "Qatar", fr: "Qatar", zones: [["Asia/Qatar"]] },
    { code: "SA", en: "Saudi Arabia", fr: "Arabie saoudite", zones: [["Asia/Riyadh"]] },
    { code: "RS", en: "Serbia", fr: "Serbie", zones: [["Europe/Belgrade"]] },
    { code: "SK", en: "Slovakia", fr: "Slovaquie", zones: [["Europe/Bratislava"]] },
    { code: "SI", en: "Slovenia", fr: "Slovénie", zones: [["Europe/Ljubljana"]] },
    { code: "LK", en: "Sri Lanka", fr: "Sri Lanka", zones: [["Asia/Colombo"]] },
    { code: "SY", en: "Syria", fr: "Syrie", zones: [["Asia/Damascus"]] },
    { code: "TW", en: "Taiwan", fr: "Taïwan", zones: [["Asia/Taipei"]] },
    { code: "TJ", en: "Tajikistan", fr: "Tadjikistan", zones: [["Asia/Dushanbe"]] },
    { code: "TZ", en: "Tanzania", fr: "Tanzanie", zones: [["Africa/Dar_es_Salaam"]] },
    { code: "TH", en: "Thailand", fr: "Thaïlande", zones: [["Asia/Bangkok"]] },
    { code: "UG", en: "Uganda", fr: "Ouganda", zones: [["Africa/Kampala"]] },
    { code: "UZ", en: "Uzbekistan", fr: "Ouzbékistan", zones: [["Asia/Tashkent"]] },
    { code: "VE", en: "Venezuela", fr: "Venezuela", zones: [["America/Caracas"]] },
    { code: "YE", en: "Yemen", fr: "Yémen", zones: [["Asia/Aden"]] },
    { code: "ZM", en: "Zambia", fr: "Zambie", zones: [["Africa/Lusaka"]] },
    { code: "ZW", en: "Zimbabwe", fr: "Zimbabwe", zones: [["Africa/Harare"]] },
    { code: "BH", en: "Bahrain", fr: "Bahreïn", zones: [["Asia/Bahrain"]] },
    { code: "LY", en: "Libya", fr: "Libye", zones: [["Africa/Tripoli"]] },
    { code: "SD", en: "Sudan", fr: "Soudan", zones: [["Africa/Khartoum"]] },
    { code: "KZ", en: "Kazakhstan", fr: "Kazakhstan", zones: [["Asia/Almaty"]] },
    { code: "MN", en: "Mongolia", fr: "Mongolie", zones: [["Asia/Ulaanbaatar"]] },
    { code: "RU", en: "Russia", fr: "Russie", zones: [
        ["Europe/Moscow", "Moscow", "Moscou"],
        ["Europe/Samara", "Samara", "Samara"],
        ["Asia/Yekaterinburg", "Yekaterinburg", "Iekaterinbourg"],
        ["Asia/Novosibirsk", "Novosibirsk", "Novossibirsk"],
        ["Asia/Krasnoyarsk", "Krasnoyarsk", "Krasnoïarsk"],
        ["Asia/Irkutsk", "Irkutsk", "Irkoutsk"],
        ["Asia/Vladivostok", "Vladivostok", "Vladivostok"]] },
    { code: "DZ", en: "Algeria", fr: "Algérie", zones: [["Africa/Algiers"]] },
    { code: "AR", en: "Argentina", fr: "Argentine", zones: [["America/Argentina/Buenos_Aires"]] },
    { code: "AU", en: "Australia", fr: "Australie", zones: [
        ["Australia/Sydney", "Sydney, Canberra", "Sydney, Canberra"],
        ["Australia/Melbourne", "Melbourne", "Melbourne"],
        ["Australia/Brisbane", "Brisbane", "Brisbane"],
        ["Australia/Adelaide", "Adelaide", "Adélaïde"],
        ["Australia/Darwin", "Darwin", "Darwin"],
        ["Australia/Perth", "Perth", "Perth"],
        ["Australia/Hobart", "Hobart", "Hobart"]] },
    { code: "AT", en: "Austria", fr: "Autriche", zones: [["Europe/Vienna"]] },
    { code: "BE", en: "Belgium", fr: "Belgique", zones: [["Europe/Brussels"]] },
    { code: "BJ", en: "Benin", fr: "Bénin", zones: [["Africa/Porto-Novo"]] },
    { code: "BR", en: "Brazil", fr: "Brésil", zones: [
        ["America/Sao_Paulo", "São Paulo, Rio de Janeiro, Brasília", "São Paulo, Rio de Janeiro, Brasília"],
        ["America/Manaus", "Manaus", "Manaus"],
        ["America/Fortaleza", "Fortaleza, Recife", "Fortaleza, Recife"],
        ["America/Rio_Branco", "Rio Branco", "Rio Branco"]] },
    { code: "BF", en: "Burkina Faso", fr: "Burkina Faso", zones: [["Africa/Ouagadougou"]] },
    { code: "CM", en: "Cameroon", fr: "Cameroun", zones: [["Africa/Douala"]] },
    { code: "CA", en: "Canada", fr: "Canada", zones: [
        ["America/Toronto", "Eastern: Toronto, Montréal, Ottawa", "Est : Toronto, Montréal, Ottawa"],
        ["America/Halifax", "Atlantic: Halifax", "Atlantique : Halifax"],
        ["America/Moncton", "Atlantic: Moncton", "Atlantique : Moncton"],
        ["America/St_Johns", "Newfoundland: St. John's", "Terre-Neuve : St. John's"],
        ["America/Winnipeg", "Central: Winnipeg", "Centre : Winnipeg"],
        ["America/Regina", "Saskatchewan: Regina", "Saskatchewan : Regina"],
        ["America/Edmonton", "Mountain: Edmonton, Calgary", "Rocheuses : Edmonton, Calgary"],
        ["America/Vancouver", "Pacific: Vancouver", "Pacifique : Vancouver"],
        ["America/Whitehorse", "Yukon: Whitehorse", "Yukon : Whitehorse"]] },
    { code: "CL", en: "Chile", fr: "Chili", zones: [["America/Santiago"]] },
    { code: "CN", en: "China", fr: "Chine", zones: [["Asia/Shanghai"]] },
    { code: "CO", en: "Colombia", fr: "Colombie", zones: [["America/Bogota"]] },
    { code: "CD", en: "Congo (DRC)", fr: "Congo (RDC)", zones: [
        ["Africa/Kinshasa", "Kinshasa", "Kinshasa"],
        ["Africa/Lubumbashi", "Lubumbashi", "Lubumbashi"]] },
    { code: "CI", en: "Côte d'Ivoire", fr: "Côte d'Ivoire", zones: [["Africa/Abidjan"]] },
    { code: "CZ", en: "Czechia", fr: "Tchéquie", zones: [["Europe/Prague"]] },
    { code: "DK", en: "Denmark", fr: "Danemark", zones: [["Europe/Copenhagen"]] },
    { code: "EG", en: "Egypt", fr: "Égypte", zones: [["Africa/Cairo"]] },
    { code: "FI", en: "Finland", fr: "Finlande", zones: [["Europe/Helsinki"]] },
    { code: "FR", en: "France", fr: "France", zones: [["Europe/Paris"]] },
    { code: "GF", en: "French Guiana", fr: "Guyane", zones: [["America/Cayenne"]] },
    { code: "PF", en: "French Polynesia", fr: "Polynésie française", zones: [["Pacific/Tahiti"]] },
    { code: "DE", en: "Germany", fr: "Allemagne", zones: [["Europe/Berlin"]] },
    { code: "GR", en: "Greece", fr: "Grèce", zones: [["Europe/Athens"]] },
    { code: "GP", en: "Guadeloupe", fr: "Guadeloupe", zones: [["America/Guadeloupe"]] },
    { code: "GN", en: "Guinea", fr: "Guinée", zones: [["Africa/Conakry"]] },
    { code: "HT", en: "Haiti", fr: "Haïti", zones: [["America/Port-au-Prince"]] },
    { code: "HU", en: "Hungary", fr: "Hongrie", zones: [["Europe/Budapest"]] },
    { code: "IN", en: "India", fr: "Inde", zones: [["Asia/Kolkata"]] },
    { code: "ID", en: "Indonesia", fr: "Indonésie", zones: [["Asia/Jakarta"]] },
    { code: "IE", en: "Ireland", fr: "Irlande", zones: [["Europe/Dublin"]] },
    { code: "IL", en: "Israel", fr: "Israël", zones: [["Asia/Jerusalem"]] },
    { code: "IT", en: "Italy", fr: "Italie", zones: [["Europe/Rome"]] },
    { code: "JP", en: "Japan", fr: "Japon", zones: [["Asia/Tokyo"]] },
    { code: "LB", en: "Lebanon", fr: "Liban", zones: [["Asia/Beirut"]] },
    { code: "LU", en: "Luxembourg", fr: "Luxembourg", zones: [["Europe/Luxembourg"]] },
    { code: "MG", en: "Madagascar", fr: "Madagascar", zones: [["Indian/Antananarivo"]] },
    { code: "ML", en: "Mali", fr: "Mali", zones: [["Africa/Bamako"]] },
    { code: "MQ", en: "Martinique", fr: "Martinique", zones: [["America/Martinique"]] },
    { code: "MU", en: "Mauritius", fr: "Maurice", zones: [["Indian/Mauritius"]] },
    { code: "MX", en: "Mexico", fr: "Mexique", zones: [
        ["America/Mexico_City", "Mexico City", "Mexico"],
        ["America/Cancun", "Cancún", "Cancún"],
        ["America/Hermosillo", "Hermosillo", "Hermosillo"],
        ["America/Tijuana", "Tijuana", "Tijuana"]] },
    { code: "MC", en: "Monaco", fr: "Monaco", zones: [["Europe/Monaco"]] },
    { code: "MA", en: "Morocco", fr: "Maroc", zones: [["Africa/Casablanca"]] },
    { code: "NL", en: "Netherlands", fr: "Pays-Bas", zones: [["Europe/Amsterdam"]] },
    { code: "NC", en: "New Caledonia", fr: "Nouvelle-Calédonie", zones: [["Pacific/Noumea"]] },
    { code: "NZ", en: "New Zealand", fr: "Nouvelle-Zélande", zones: [["Pacific/Auckland"]] },
    { code: "NE", en: "Niger", fr: "Niger", zones: [["Africa/Niamey"]] },
    { code: "NG", en: "Nigeria", fr: "Nigeria", zones: [["Africa/Lagos"]] },
    { code: "NO", en: "Norway", fr: "Norvège", zones: [["Europe/Oslo"]] },
    { code: "PE", en: "Peru", fr: "Pérou", zones: [["America/Lima"]] },
    { code: "PH", en: "Philippines", fr: "Philippines", zones: [["Asia/Manila"]] },
    { code: "PL", en: "Poland", fr: "Pologne", zones: [["Europe/Warsaw"]] },
    { code: "PT", en: "Portugal", fr: "Portugal", zones: [
        ["Europe/Lisbon", "Lisbon", "Lisbonne"],
        ["Atlantic/Azores", "Azores", "Açores"]] },
    { code: "RE", en: "Réunion", fr: "La Réunion", zones: [["Indian/Reunion"]] },
    { code: "RO", en: "Romania", fr: "Roumanie", zones: [["Europe/Bucharest"]] },
    { code: "RW", en: "Rwanda", fr: "Rwanda", zones: [["Africa/Kigali"]] },
    { code: "SN", en: "Senegal", fr: "Sénégal", zones: [["Africa/Dakar"]] },
    { code: "SG", en: "Singapore", fr: "Singapour", zones: [["Asia/Singapore"]] },
    { code: "ZA", en: "South Africa", fr: "Afrique du Sud", zones: [["Africa/Johannesburg"]] },
    { code: "KR", en: "South Korea", fr: "Corée du Sud", zones: [["Asia/Seoul"]] },
    { code: "ES", en: "Spain", fr: "Espagne", zones: [
        ["Europe/Madrid", "Madrid", "Madrid"],
        ["Atlantic/Canary", "Canary Islands", "Îles Canaries"]] },
    { code: "PM", en: "Saint Pierre and Miquelon", fr: "Saint-Pierre-et-Miquelon", zones: [["America/Miquelon"]] },
    { code: "SE", en: "Sweden", fr: "Suède", zones: [["Europe/Stockholm"]] },
    { code: "CH", en: "Switzerland", fr: "Suisse", zones: [["Europe/Zurich"]] },
    { code: "TG", en: "Togo", fr: "Togo", zones: [["Africa/Lome"]] },
    { code: "TN", en: "Tunisia", fr: "Tunisie", zones: [["Africa/Tunis"]] },
    { code: "TR", en: "Türkiye", fr: "Turquie", zones: [["Europe/Istanbul"]] },
    { code: "UA", en: "Ukraine", fr: "Ukraine", zones: [["Europe/Kyiv"]] },
    { code: "AE", en: "United Arab Emirates", fr: "Émirats arabes unis", zones: [["Asia/Dubai"]] },
    { code: "GB", en: "United Kingdom", fr: "Royaume-Uni", zones: [["Europe/London"]] },
    { code: "US", en: "United States", fr: "États-Unis", zones: [
        ["America/New_York", "Eastern: New York, Miami", "Est : New York, Miami"],
        ["America/Chicago", "Central: Chicago, Dallas", "Centre : Chicago, Dallas"],
        ["America/Denver", "Mountain: Denver", "Rocheuses : Denver"],
        ["America/Phoenix", "Arizona: Phoenix", "Arizona : Phoenix"],
        ["America/Los_Angeles", "Pacific: Los Angeles, Seattle", "Pacifique : Los Angeles, Seattle"],
        ["America/Anchorage", "Alaska: Anchorage", "Alaska : Anchorage"],
        ["Pacific/Honolulu", "Hawaii: Honolulu", "Hawaï : Honolulu"]] },
    { code: "UY", en: "Uruguay", fr: "Uruguay", zones: [["America/Montevideo"]] },
    { code: "VN", en: "Vietnam", fr: "Viêt Nam", zones: [["Asia/Ho_Chi_Minh"]] }
]

// The countries in the page's language, sorted, matching a search.
function sorted(lang, search) {
    var key = lang === "fr" ? "fr" : "en"
    var needle = plain(search)
    return list.filter(function (c) { return needle === "" || plain(c[key]).indexOf(needle) >= 0 })
               .sort(function (a, b) { return a[key].localeCompare(b[key], key) })
}

// the country a time zone belongs to, or null
function ofZone(zone) {
    for (var i = 0; i < list.length; ++i)
        for (var j = 0; j < list[i].zones.length; ++j)
            if (list[i].zones[j][0] === zone)
                return list[i]
    return null
}

function zoneLabel(country, zone, lang) {
    for (var j = 0; j < country.zones.length; ++j)
        if (country.zones[j][0] === zone)
            return country.zones[j][lang === "fr" ? 2 : 1] || ""
    return ""
}

// lower case, no accents: "etats" finds "États-Unis"
function plain(text) {
    return String(text || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim()
}
