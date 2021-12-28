
#include <string>

class Overload
{
public:
    Overload( void );
    Overload( int x );

    ~Overload( void );

    /// Parameters:
    ///  x - Number to round
    /// Returns:
    ///  Number rounded to nearest integer.
    int round( float x );

    int round( double x );

    int round( long double x );

    /// Convert string to uppercase.
    ///
    /// Parameters:
    ///  str - String to convert
    std::string toUpper( const char *str );

    std::string toUpper( const std::string &str );
};

