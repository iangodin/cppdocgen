
#include <string>

/// Class with overloaded constructors and methods.
class Overload
{
public:
    /// First overloaded constructor.
    Overload( void );

    /// Second overloaded constructor.
    Overload( int x );

    /// Destructor.
    ~Overload( void );

    /// Parameters:
    ///  x - Number to round
    /// Returns:
    ///  Number rounded to nearest integer.
    int round( float x );

    /// Second overloaded round.
    int round( double x );

    /// Third overloaded round.
    int round( long double x );

    /// Convert string to uppercase.
    ///
    /// Parameters:
    ///  str - String to convert
    std::string toUpper( const char *str );

    /// Overload with std::string type.
    std::string toUpper( const std::string &str );
};

